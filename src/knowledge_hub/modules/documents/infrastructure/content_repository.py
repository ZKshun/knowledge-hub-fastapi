from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from knowledge_hub.core.errors import InvalidDocumentContent
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure.content_record import (
    ContentSnapshot,
    DocumentContentRecord,
)
from knowledge_hub.modules.documents.infrastructure.mappers import as_utc
from knowledge_hub.modules.documents.infrastructure.operation_types import OperationRecord
from knowledge_hub.modules.documents.infrastructure.write_create import creation_tombstone


class ContentRepository:
    def __init__(self, collection: AsyncCollection[DocumentContentRecord]) -> None:
        self.collection = collection

    async def insert_creation(self, record: DocumentContentRecord) -> None:
        # Mongoose required string rejects empty content on create, but updateOne
        # does not enable validators: do not apply this rule to later PATCH writes.
        if record["content"] == "":
            raise InvalidDocumentContent("Document content must not be empty on create")
        await self.collection.insert_one(record)

    async def has_document(self, document_id: DocumentId) -> bool:
        return (
            await self.collection.find_one({"documentId": str(document_id)}, {"_id": 1}) is not None
        )

    async def compensate_creation(self, operation: OperationRecord) -> None:
        tombstone = creation_tombstone(operation)
        # Keeping the unique _id reservation makes an already-sent, late insert fail.
        # Match operation/version too: a foreign or newer body must never be erased.
        await self.collection.replace_one(
            {
                "_id": tombstone["_id"],
                "documentId": str(operation.document_id),
                "operationId": operation.operation_id,
                "version": 1,
            },
            tombstone,
            upsert=True,
        )

    async def get(self, content_id: str) -> ContentSnapshot | None:
        record = await self.collection.find_one({"_id": ObjectId(content_id), "deleted": False})
        if record is None:
            return None
        return ContentSnapshot(
            content_id=str(record["_id"]),
            document_id=DocumentId(record["documentId"]),
            content=record["content"],
            content_length=record["contentLength"],
            content_summary=record["contentSummary"],
            version=record["version"],
            deleted=record["deleted"],
            created_at=as_utc(record["createdAt"]),
            updated_at=as_utc(record["updatedAt"]),
            operation_id=record.get("operationId"),
        )
