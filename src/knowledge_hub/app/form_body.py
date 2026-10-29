import re
from urllib.parse import unquote_plus

from knowledge_hub.integrations.http.errors import BodyDecodingError


def parse_form(text: str, charset: str) -> dict[str, object]:
    if not text:
        return {}
    pairs = text.split("&")
    if len(pairs) > 1000:
        raise BodyDecodingError(413, "too many parameters")
    result: dict[str, object] = {}
    for pair in pairs:
        raw_key, _, raw_value = pair.partition("=")
        key, value = _decode(raw_key, charset), _decode(raw_value, charset)
        if key.count("[") > 32:
            raise BodyDecodingError(400, "The input exceeded the depth")
        root, key = _root_key(key, result)
        if not root or root == "__proto__":
            continue
        if "[" in key:
            # Every v1 DTO field is scalar: preserve nested/array shape for rejection.
            value_object: object = (
                {"nested": value} if re.search(r"\[[^]0-9][^]]*\]", key) else [value]
            )
        else:
            value_object = value
        if root in result:
            previous = result[root]
            result[root] = (
                [*previous, value_object]
                if isinstance(previous, list)
                else [previous, value_object]
            )
        else:
            result[root] = value_object
    return result


def _root_key(key: str, result: dict[str, object]) -> tuple[str, str]:
    root = key.split("[", 1)[0]
    if root or not key.startswith("["):
        return root, key
    closing = key.find("]")
    if closing <= 0:
        return "", key
    root = key[1:closing]
    if not root:
        index = 0
        while str(index) in result:
            index += 1
        root = str(index)
    return root, root + key[closing + 1 :]


def _decode(value: str, charset: str) -> str:
    try:
        return unquote_plus(value, encoding=charset, errors="strict")
    except UnicodeDecodeError:
        return value.replace("+", " ")
