import json
from email.message import Message

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import Receive, Scope

from knowledge_hub.app.form_body import parse_form
from knowledge_hub.app.json_errors import validate_json
from knowledge_hub.integrations.http.compression import BodyDecompressor
from knowledge_hub.integrations.http.errors import BodyDecodingError

_CODECS = {
    "utf8": "utf-8",
    "utf16le": "utf-16-le",
    "utf16be": "utf-16-be",
    "utf32le": "utf-32-le",
    "utf32be": "utf-32-be",
    "utf7": "utf-7",
    "utf16": "utf-16",
    "utf32": "utf-32",
}


async def prepare_request_body(scope: Scope, receive: Receive) -> tuple[bool, bytes | None]:
    headers = Headers(scope=scope)
    content_type = headers.get("content-type", "")
    media_type = content_type.split(";", 1)[0].strip().lower()
    recognized = media_type in ("application/json", "application/x-www-form-urlencoded")
    has_body = "content-length" in headers or "transfer-encoding" in headers
    if not recognized or not has_body:
        path = scope["path"].split("/")
        document_body = (
            scope["method"] == "POST"
            and path == ["", "documents"]
            or scope["method"] == "PATCH"
            and len(path) == 3
            and path[1] == "documents"
        )
        return (True, b"") if document_body else (False, None)
    form = media_type == "application/x-www-form-urlencoded"
    charset = _charset(content_type, form=form)
    body = await _read_body(receive, headers.get("content-encoding", "identity").lower())
    if body is None:
        return True, None
    text = _decode(body, charset)
    if form:
        data: object = parse_form(text, charset)
        MutableHeaders(scope=scope)["content-type"] = "application/json"
    else:
        error = validate_json(text)
        if error:
            raise BodyDecodingError(400, error, error_label="Bad Request")
        data = json.loads(text, parse_int=float, parse_float=float) if text else {}
    # Replay decoded values, so charset replacement and JS Number survive FastAPI's parser.
    return True, json.dumps(data, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def _charset(content_type: str, *, form: bool) -> str:
    message = Message()
    message["content-type"] = content_type
    charset = message.get_content_charset("utf-8")
    supported = (
        charset in ("utf-8", "iso-8859-1")
        if form
        else charset.startswith("utf-") and charset.replace("-", "").replace("_", "") in _CODECS
    )
    if not supported:
        raise BodyDecodingError(415, f'unsupported charset "{charset.upper()}"')
    return charset


def _decode(body: bytes, charset: str) -> str:
    key = charset.replace("-", "").replace("_", "")
    codec = _CODECS.get(key, charset)
    if key == "utf16" and not body.startswith((b"\xff\xfe", b"\xfe\xff")):
        codec = "utf-16-be" if body[:2].startswith(b"\0") else "utf-16-le"
    if key == "utf32" and not body.startswith((b"\xff\xfe\0\0", b"\0\0\xfe\xff")):
        codec = "utf-32-be" if body[:4].startswith(b"\0\0") else "utf-32-le"
    return body.decode(codec, errors="replace").removeprefix("\ufeff")


async def _read_body(receive: Receive, encoding: str) -> bytes | None:
    decoder = BodyDecompressor(encoding)
    chunks = []
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            return None
        decoded = decoder.feed(message.get("body", b""))
        if decoded:
            chunks.append(decoded)
        if not message.get("more_body", False):
            decoder.finish()
            return b"".join(chunks)
