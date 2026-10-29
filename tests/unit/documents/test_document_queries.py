from datetime import UTC, datetime

import pytest

from knowledge_hub.core.errors import DocumentNotFound
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.application.queries.get_document import get_document
from knowledge_hub.modules.documents.application.queries.list_documents import list_documents
from knowledge_hub.modules.documents.domain.commands import DocumentQuery
from knowledge_hub.modules.documents.domain.document import Document, DocumentDetail, DocumentPage


class ReadingStore:
    def __init__(self, detail: DocumentDetail | None) -> None:
        self.detail = detail
        self.query: DocumentQuery | None = None

    async def get(self, document_id: DocumentId) -> DocumentDetail | None:
        return self.detail if self.detail and self.detail.document.id == document_id else None

    async def page(self, query: DocumentQuery) -> DocumentPage:
        self.query = query
        return DocumentPage(items=(), total=0, page=query.page, page_size=query.page_size)


async def test_missing_detail_raises_legacy_business_error() -> None:
    with pytest.raises(DocumentNotFound, match="Document 123 not found"):
        await get_document(DocumentId("123"), store=ReadingStore(None))


async def test_existing_detail_is_returned_with_opaque_string_id() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    detail = DocumentDetail(
        document=Document(
            id=DocumentId("9007199254740993"), title="T", created_at=now, updated_at=now
        ),
        content="body",
    )
    assert await get_document(detail.document.id, store=ReadingStore(detail)) == detail


async def test_page_keeps_normalized_query_and_original_envelope() -> None:
    store = ReadingStore(None)
    query = DocumentQuery(title="Alpha", status=999, page=2, page_size=1)
    page = await list_documents(query, store=store)
    assert store.query == query
    assert page == DocumentPage(items=(), total=0, page=2, page_size=1)
