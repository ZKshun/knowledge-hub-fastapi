from base64 import b64decode, b64encode

from knowledge_hub.core.errors import OperationRecoveryError
from knowledge_hub.modules.documents.infrastructure.operation_types import JsonValue


def encode_snapshot_text(value: str) -> str:
    # BSON permits NUL in strings; PostgreSQL JSONB does not. Encoding is lossless,
    # not encryption: private snapshots still require database access control.
    return b64encode(value.encode("utf-8")).decode("ascii")


def decode_snapshot_text(value: JsonValue) -> str:
    if not isinstance(value, str):
        raise OperationRecoveryError("Invalid encoded recovery text")
    return b64decode(value, validate=True).decode("utf-8")
