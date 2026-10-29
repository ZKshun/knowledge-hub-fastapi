from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

from knowledge_hub.core.identifiers import DocumentId


class DocumentStatus(IntEnum):
    DRAFT = 0
    PUBLISHED = 1
    ARCHIVED = 2


@dataclass(frozen=True, slots=True, kw_only=True)
class Document:
    id: DocumentId
    title: str
    created_at: datetime
    updated_at: datetime
    content_id: str | None = None
    summary: str | None = None
    category_id: str | None = None
    team_id: str | None = None
    author_id: str | None = None
    cover_image: str | None = None
    tags: str | None = None
    status: DocumentStatus = DocumentStatus.DRAFT
    remark: str | None = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    favourite_count: int = 0
    word_count: int = 0
    publish_time: datetime | None = None
    is_public: bool = False
    create_by: str | None = None
    update_by: str | None = None
    deleted: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentDetail:
    document: Document
    content: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentPage:
    items: tuple[Document, ...]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteDocumentResult:
    document_id: DocumentId
    deleted: bool
