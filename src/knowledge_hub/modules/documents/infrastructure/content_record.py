from dataclasses import dataclass
from datetime import datetime
from typing import NotRequired, TypedDict

from bson import ObjectId

from knowledge_hub.core.identifiers import DocumentId


class DocumentContentRecord(TypedDict):
    _id: ObjectId
    documentId: str
    content: str
    contentLength: int
    contentSummary: str | None
    version: int
    deleted: bool
    createdAt: datetime
    updatedAt: datetime
    operationId: NotRequired[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class ContentSnapshot:
    content_id: str
    document_id: DocumentId
    content: str
    content_length: int
    content_summary: str | None
    version: int
    deleted: bool
    created_at: datetime
    updated_at: datetime
    operation_id: str | None
