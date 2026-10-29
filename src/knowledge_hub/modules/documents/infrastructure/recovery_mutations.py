from datetime import datetime

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection

from knowledge_hub.core.errors import OperationRecoveryError
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord
from knowledge_hub.modules.documents.infrastructure.operation_types import OperationRecord
from knowledge_hub.modules.documents.infrastructure.snapshot_encoding import decode_snapshot_text


async def compensate_mutation(
    collection: AsyncCollection[DocumentContentRecord], operation: OperationRecord
) -> None:
    before = operation.snapshot["before"]
    if before is None:
        return
    if not isinstance(before, dict):
        raise OperationRecoveryError("Invalid mutation recovery snapshot")
    updated_at = before.get("updatedAt")
    if not isinstance(updated_at, str):
        raise OperationRecoveryError("Invalid mutation recovery timestamp")
    rollback_fence = f"rollback:{operation.operation_id}"
    restore: dict[str, object] = {
        key: before[key] for key in ("contentLength", "version", "deleted")
    }
    restore["content"] = decode_snapshot_text(before["content_base64"])
    restore["contentSummary"] = (
        decode_snapshot_text(before["summary_base64"])
        if before["summary_base64"] is not None
        else None
    )
    restore.update(updatedAt=datetime.fromisoformat(updated_at), operationId=rollback_fence)
    # Fence the original state too: a timed-out Mongo request may not have arrived yet.
    # Never restore the old token when rolling back the public version (ABA protection).
    result = await collection.find_one_and_update(
        {
            "_id": ObjectId(str(operation.snapshot["content_id"])),
            "documentId": str(operation.document_id),
            "$or": [
                {"version": operation.expected_version, "operationId": before["operationId"]},
                {
                    "version": operation.snapshot["applied_version"],
                    "operationId": operation.operation_id,
                },
                {"version": operation.expected_version, "operationId": rollback_fence},
            ],
        },
        {"$set": restore},
        return_document=ReturnDocument.AFTER,
    )
    if result is None:
        raise OperationRecoveryError("Recovery body is missing or has a foreign operation/version")
