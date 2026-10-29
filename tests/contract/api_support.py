from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from knowledge_hub.core.errors import DocumentNotFound
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.domain.commands import DocumentMutation, DocumentQuery
from knowledge_hub.modules.documents.domain.document import DocumentDetail, DocumentPage

NOW = datetime(2026, 1, 1, 0, 0, 0, 123456, tzinfo=UTC)


class MemoryStore:
    def __init__(self) -> None:
        self.documents: dict[DocumentId, DocumentDetail] = {}
        self.query: DocumentQuery | None = None

    async def create(self, draft: DocumentDetail) -> DocumentDetail:
        saved = replace(
            draft, document=replace(draft.document, content_id="0123456789abcdef01234567")
        )
        self.documents[saved.document.id] = saved
        return saved

    async def get(self, document_id: DocumentId) -> DocumentDetail | None:
        return self.documents.get(document_id)

    async def page(self, query: DocumentQuery) -> DocumentPage:
        self.query = query
        return DocumentPage(
            items=tuple(d.document for d in self.documents.values()),
            total=len(self.documents),
            page=query.page,
            page_size=query.page_size,
        )

    async def mutate(
        self, document_id: DocumentId, transform: Callable[[DocumentDetail], DocumentMutation]
    ) -> DocumentDetail:
        if document_id not in self.documents:
            raise DocumentNotFound(document_id)
        saved = transform(self.documents[document_id]).target
        self.documents[document_id] = saved
        return saved

    async def soft_delete(self, document_id: DocumentId) -> None:
        if document_id not in self.documents:
            raise DocumentNotFound(document_id)
        del self.documents[document_id]
