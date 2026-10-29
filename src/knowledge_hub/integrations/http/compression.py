import zlib

import brotli

from knowledge_hub.integrations.http.errors import BodyDecodingError


class BodyDecompressor:
    def __init__(self, encoding: str, *, limit: int = 100 * 1024) -> None:
        if encoding not in ("identity", "gzip", "deflate", "br"):
            raise BodyDecodingError(415, f'unsupported content encoding "{encoding}"')
        self.encoding, self.limit, self.size = encoding, limit, 0
        self._brotli = brotli.Decompressor() if encoding == "br" else None
        self._zlib = (
            zlib.decompressobj(31 if encoding == "gzip" else 15)
            if encoding in ("gzip", "deflate")
            else None
        )

    def feed(self, data: bytes) -> bytes:
        try:
            if self.encoding == "identity":
                return self._take(data)
            if self._brotli is not None:
                return self._decode_brotli(data)
            return self._decode_zlib(data)
        except zlib.error as error:
            raise BodyDecodingError(400, str(error).split(": ", 1)[-1]) from None
        except brotli.error:
            raise BodyDecodingError(400, "Decompression failed") from None

    def _take(self, data: bytes) -> bytes:
        self.size += len(data)
        if self.size > self.limit:
            raise BodyDecodingError(413, "request entity too large")
        return data

    def _decode_brotli(self, data: bytes) -> bytes:
        assert self._brotli is not None
        output = [
            self._take(self._brotli.process(data, output_buffer_limit=self.limit - self.size + 1))
        ]
        while not self._brotli.can_accept_more_data():
            output.append(
                self._take(
                    self._brotli.process(b"", output_buffer_limit=self.limit - self.size + 1)
                )
            )
        return b"".join(output)

    def _decode_zlib(self, data: bytes) -> bytes:
        assert self._zlib is not None
        output = []
        while data:
            output.append(self._take(self._zlib.decompress(data, self.limit - self.size + 1)))
            data = self._zlib.unconsumed_tail
            if self.encoding == "gzip" and self._zlib.unused_data:
                data = self._zlib.unused_data
                self._zlib = zlib.decompressobj(31)
        return b"".join(output)

    def finish(self) -> None:
        finished = (
            self._brotli.is_finished() if self._brotli else self._zlib.eof if self._zlib else True
        )
        if not finished:
            raise BodyDecodingError(400, "unexpected end of file")
