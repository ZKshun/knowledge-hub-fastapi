from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from knowledge_hub.modules.documents.domain.document import DocumentDetail
from knowledge_hub.modules.documents.infrastructure.content_record import ContentSnapshot
from knowledge_hub.modules.documents.infrastructure.operation_types import (
    JsonValue,
    OperationKind,
    OperationRecord,
)
from knowledge_hub.modules.documents.infrastructure.snapshot_encoding import encode_snapshot_text


@dataclass(frozen=True, slots=True)
class MutationPlan:
    operation: OperationRecord
    detail: DocumentDetail
    changes: dict[str, object]


def plan_mutation(
    kind: OperationKind,
    current: DocumentDetail,
    target: DocumentDetail,
    content: ContentSnapshot | None,
    changes: dict[str, object],
) -> MutationPlan:
    now = datetime.now(UTC)
    before: JsonValue = None
    if content is not None and changes:
        before = {
            "content_base64": encode_snapshot_text(content.content),
            "contentLength": content.content_length,
            "summary_base64": encode_snapshot_text(content.content_summary)
            if content.content_summary is not None
            else None,
            "version": content.version,
            "deleted": content.deleted,
            "updatedAt": content.updated_at.isoformat(),
            "operationId": content.operation_id,
        }
    version = changes.get("version", content.version if content else None)
    operation = OperationRecord(
        operation_id=str(uuid4()),
        document_id=current.document.id,
        operation_type=kind,
        state="prepared",
        expected_version=content.version if before is not None and content else None,
        snapshot={
            "content_id": current.document.content_id,
            "metadata_updated_at": current.document.updated_at.isoformat(),
            "before": before,
            "applied_version": version if isinstance(version, int) else None,
        },
        last_error=None,
        created_at=now,
        updated_at=now,
    )
    return MutationPlan(operation=operation, detail=target, changes=changes)
