from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from knowledge_hub.core.identifiers import DocumentId

type OperationKind = Literal["create", "update", "delete"]
type OperationState = Literal["prepared", "completed", "compensation_pending", "compensated"]
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationRecord:
    operation_id: str
    document_id: DocumentId
    operation_type: OperationKind
    state: OperationState
    expected_version: int | None
    snapshot: dict[str, JsonValue]
    last_error: str | None
    created_at: datetime
    updated_at: datetime
