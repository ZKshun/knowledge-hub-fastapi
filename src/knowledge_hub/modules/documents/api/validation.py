from collections.abc import Mapping


class LegacyValidationError(Exception):
    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("Request validation failed")


BODY_FIELDS = (
    "title",
    "content",
    "summary",
    "categoryId",
    "teamId",
    "authorId",
    "coverImage",
    "tags",
    "status",
    "remark",
    "isPublic",
    "createBy",
)
ENUM_LABELS = ("Draft", "Published", "Archived")


def object_fields(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        # class-transformer drops these prototype keys before whitelist validation.
        return {
            str(key): item for key, item in value.items() if key not in ("__proto__", "constructor")
        }
    if isinstance(value, list):
        return {str(index): item for index, item in enumerate(value)}
    return {}


def validate_body(value: object, *, partial: bool) -> dict[str, object]:
    data = object_fields(value)
    fields = ("updateBy", *BODY_FIELDS[:-1]) if partial else BODY_FIELDS
    messages = [f"property {key} should not exist" for key in data if key not in fields]
    for field in fields:
        item = data.get(field)
        if item is None and (partial or field not in ("title", "content")):
            continue
        message = _field_error(field, item)
        if message:
            messages.append(message)
        elif field == "status" and isinstance(item, float):
            data[field] = int(item)
    if messages:
        raise LegacyValidationError(messages)
    return data


def _field_error(field: str, value: object) -> str | None:
    if field == "status":
        if type(value) in (int, float) and value in (0, 1, 2) or value in ENUM_LABELS:
            return None
        return "status must be one of the following values: 0, 1, 2"
    if field == "isPublic":
        return None if isinstance(value, bool) else "isPublic must be a boolean value"
    return None if isinstance(value, str) else f"{field} must be a string"
