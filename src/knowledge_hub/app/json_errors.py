import json
import re

from knowledge_hub.app.json_tokens import lexical_error
from knowledge_hub.modules.documents.domain.text_metrics import content_length

_TOKENS = re.compile(r'"(?:[^"\\]|\\.)*"|(?P<constant>-?Infinity|NaN)', re.DOTALL)


class NonFiniteJSON(ValueError):
    pass


def _nonfinite(value: str) -> None:
    raise NonFiniteJSON(value)


def validate_json(text: str) -> str | None:
    if text == "":
        return None
    first = re.search(r"[^ \t\r\n]", text)
    if first is not None and first[0] not in ("{", "["):
        return unexpected_token(text, first.start())
    try:
        json.loads(text, parse_int=float, parse_float=float, parse_constant=_nonfinite)
    except NonFiniteJSON:
        token = next(match for match in _TOKENS.finditer(text) if match["constant"])
        if token["constant"].startswith("-"):
            return position_error("No number after minus sign in JSON", text, token.start() + 1)
        return unexpected_token(text, token.start())
    except json.JSONDecodeError as error:
        return syntax_error(text, error)
    return None


def unexpected_token(text: str, position: int) -> str:
    start, end = (
        (0, len(text)) if len(text) < 20 else (max(0, position - 10), min(len(text), position + 10))
    )
    excerpt = ("..." if start else "") + f'"{text[start:end]}"' + ("..." if end < len(text) else "")
    return f"Unexpected token '{text[position]}', {excerpt} is not valid JSON"


def position_error(description: str, text: str, position: int) -> str:
    prefix = text[:position]
    lines = re.split(r"\r\n|[\r\n]", prefix)
    return f"{description} at position {content_length(prefix)} (line {len(lines)} column {content_length(lines[-1]) + 1})"


def syntax_error(text: str, error: json.JSONDecodeError) -> str:
    message, position = error.msg, error.pos
    if message.startswith("Unterminated string"):
        return position_error("Unterminated string in JSON", text, len(text))
    if message.startswith("Invalid \\u"):
        position += 1
        while position < len(text) and text[position] in "0123456789abcdefABCDEF":
            position += 1
        return position_error("Bad Unicode escape in JSON", text, position)
    if message.startswith("Invalid \\escape"):
        return position_error("Bad escaped character in JSON", text, position + 1)
    if message.startswith("Invalid control character"):
        return position_error("Bad control character in string literal in JSON", text, position)
    if message in ("Expecting value", "Expecting ',' delimiter"):
        issue = lexical_error(text, position)
        if issue is not None:
            description, position = issue
            if description == "end":
                return "Unexpected end of JSON input"
            if description == "token":
                return unexpected_token(text, position)
            return position_error(description, text, position)
    return _structural_error(text, position, message)


def _structural_error(text: str, position: int, message: str) -> str:
    if message.startswith("Expecting property name"):
        previous = text[:position].rstrip(" \t\r\n")
        description = (
            "Expected double-quoted property name in JSON"
            if previous.endswith(",")
            else "Expected property name or '}' in JSON"
        )
    elif message == "Expecting ':' delimiter":
        description = "Expected ':' after property name in JSON"
    elif message == "Extra data":
        description = "Unexpected non-whitespace character after JSON"
    elif message == "Expecting ',' delimiter":
        if (
            position
            and text[position - 1] == "0"
            and text[position : position + 1] in "0123456789"
            and position < len(text)
        ):
            description = "Unexpected number in JSON"
        else:
            container = _container(text[:position])
            description = (
                "Expected ',' or ']' after array element in JSON"
                if container == "["
                else "Expected ',' or '}' after property value in JSON"
            )
    elif position >= len(text):
        return "Unexpected end of JSON input"
    else:
        return unexpected_token(text, position)
    return position_error(description, text, position)


def _container(prefix: str) -> str | None:
    stack: list[str] = []
    in_string = escaped = False
    for character in prefix:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "[{":
            stack.append(character)
        elif character in "]}" and stack:
            stack.pop()
    return stack[-1] if stack else None
