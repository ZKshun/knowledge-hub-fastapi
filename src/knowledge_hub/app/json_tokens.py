import re

_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|[-0-9tfn]', re.DOTALL)


def lexical_error(text: str, position: int) -> tuple[str, int] | None:
    skip = 0
    for match in _TOKEN.finditer(text):
        start, token = match.start(), match[0]
        if start > position:
            break
        if start < skip or token.startswith('"'):
            continue
        if token in "tfn":
            skip, issue = _literal(text, start, {"t": "true", "f": "false", "n": "null"}[token])
        else:
            skip, issue = _number(text, start)
        if issue is not None:
            return issue
    return None


def _literal(text: str, start: int, expected: str) -> tuple[int, tuple[str, int] | None]:
    for offset, character in enumerate(expected):
        position = start + offset
        if position >= len(text):
            return position, ("end", position)
        if text[position] != character:
            return position, ("token", position)
    return start + len(expected), None


def _digits(text: str, position: int) -> int:
    while position < len(text) and text[position] in "0123456789":
        position += 1
    return position


def _number(text: str, start: int) -> tuple[int, tuple[str, int] | None]:
    position = start
    if text[position] == "-":
        position += 1
        if position >= len(text) or text[position] not in "0123456789":
            return position, ("No number after minus sign in JSON", position)
    if text[position] == "0":
        position += 1
        if position < len(text) and text[position] in "0123456789":
            return position, ("Unexpected number in JSON", position)
    else:
        position = _digits(text, position)
    return _number_suffix(text, position)


def _number_suffix(text: str, position: int) -> tuple[int, tuple[str, int] | None]:
    if text[position : position + 1] == ".":
        position += 1
        end = _digits(text, position)
        if end == position:
            return position, ("Unterminated fractional number in JSON", position)
        position = end
    if position < len(text) and text[position] in "eE":
        position += 1
        if position < len(text) and text[position] in "+-":
            position += 1
        end = _digits(text, position)
        if end == position:
            return position, ("Exponent part is missing a number in JSON", position)
        position = end
    return position, None
