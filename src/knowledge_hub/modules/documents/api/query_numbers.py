import math
import re

from knowledge_hub.modules.documents.api.validation import LegacyValidationError, object_fields

_SPACE = (
    "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006"
    "\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)
_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_RADIX = re.compile(r"0(?:[xX][0-9a-fA-F]+|[oO][0-7]+|[bB][01]+)\Z")
_QUERY_FIELDS = ("title", "categoryId", "teamId", "authorId", "status", "page", "pageSize")


def javascript_number(value: object) -> float:
    if not isinstance(value, str):
        return math.nan
    text = value.strip(_SPACE)
    if not text:
        return 0.0
    if text in ("Infinity", "+Infinity", "-Infinity"):
        return float(text)
    try:
        if _RADIX.fullmatch(text):
            return float(int(text, 0))
        return float(text) if _DECIMAL.fullmatch(text) else math.nan
    except (ValueError, OverflowError):
        return math.nan


def validate_query(value: object) -> dict[str, object]:
    data = object_fields(value)
    messages = [f"property {key} should not exist" for key in data if key not in _QUERY_FIELDS]
    for field in _QUERY_FIELDS:
        if field not in data or data[field] is None:
            continue
        if field in ("status", "page", "pageSize"):
            number = javascript_number(data[field])
            messages.extend(_number_errors(field, number))
            if math.isfinite(number) and number.is_integer():
                data[field] = int(number)
        elif not isinstance(data[field], str):
            messages.append(f"{field} must be a string")
    if messages:
        raise LegacyValidationError(messages)
    return data


def _number_errors(field: str, value: float) -> list[str]:
    errors = []
    if field == "pageSize" and not value <= 100:
        errors.append("pageSize must not be greater than 100")
    if field != "status" and not value >= 1:
        errors.append(f"{field} must not be less than 1")
    if not math.isfinite(value) or not value.is_integer():
        errors.append(f"{field} must be an integer number")
    return errors
