from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import uuid4

from bson import ObjectId

from knowledge_hub.core.errors import OperationRecoveryError
from knowledge_hub.modules.documents.domain.document import DocumentDetail
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord
from knowledge_hub.modules.documents.infrastructure.mappers import make_content_record
from knowledge_hub.modules.documents.infrastructure.operation_types import OperationRecord


@dataclass(frozen=True, slots=True)
class CreationPlan:
    operation: OperationRecord
    content: DocumentContentRecord
    detail: DocumentDetail


def plan_creation(draft: DocumentDetail) -> CreationPlan:
    operation_id = str(uuid4())
    content = make_content_record(
        draft.document.id,
        draft.content,
        now=draft.document.created_at,
        summary=draft.document.summary,
        operation_id=operation_id,
    )
    content_id = str(content["_id"])
    operation = OperationRecord(
        operation_id=operation_id,
        document_id=draft.document.id,
        operation_type="create",
        state="prepared",
        expected_version=None,
        snapshot={"content_id": content_id},
        last_error=None,
        created_at=draft.document.created_at,
        updated_at=draft.document.updated_at,
    )
    detail = replace(draft, document=replace(draft.document, content_id=content_id))
    return CreationPlan(operation, content, detail)


def creation_tombstone(operation: OperationRecord) -> DocumentContentRecord:
    content_id = operation.snapshot.get("content_id")
    if not isinstance(content_id, str):
        raise OperationRecoveryError("Create recovery snapshot lacks a content ID")
    return {
        "_id": ObjectId(content_id),
        "documentId": str(operation.document_id),
        "content": "",
        "contentLength": 0,
        "contentSummary": "",
        "version": 1,
        "deleted": True,
        "createdAt": operation.created_at,
        "updatedAt": datetime.now(UTC),
        "operationId": operation.operation_id,
        "creationFence": True,
    }
