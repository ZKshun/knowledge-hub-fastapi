from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure.content_record import (
    ContentSnapshot,
    DocumentContentRecord,
)
from knowledge_hub.modules.documents.infrastructure.mappers import as_utc


class ContentRepository:
    def __init__(self, collection: AsyncCollection[DocumentContentRecord]) -> None:
        self.collection = collection

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
