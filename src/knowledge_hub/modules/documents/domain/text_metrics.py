import re

# ECMAScript whitespace excludes Python's NEL/control separators, and includes BOM.
_JS_WHITESPACE = (
    "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)
_WHITESPACE_RUN = re.compile(f"[{_JS_WHITESPACE}]+")
_CJK = re.compile("[\u4e00-\u9fff]")


def count_words(content: str) -> int:
    trimmed = content.strip(_JS_WHITESPACE)
    remaining = _CJK.sub(" ", trimmed).strip(_JS_WHITESPACE)
    tokens = [token for token in _WHITESPACE_RUN.split(remaining) if token]
    return len(_CJK.findall(trimmed)) + len(tokens)


def content_length(content: str) -> int:
    return len(content.encode("utf-16-le", errors="surrogatepass")) // 2


def build_content_summary(content: str, max_length: int = 200) -> str:
    if type(max_length) is not int or max_length < 0:
        raise ValueError("max_length must be a nonnegative integer")
    trimmed = _WHITESPACE_RUN.sub(" ", content.strip(_JS_WHITESPACE))
    encoded = trimmed.encode("utf-16-le", errors="surrogatepass")
    if len(encoded) <= max_length * 2:
        return trimmed
    # JS slice may leave an unpaired surrogate; BSON/HTTP adapters own its encoding.
    return encoded[: max_length * 2].decode("utf-16-le", errors="surrogatepass") + "..."
