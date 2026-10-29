from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from knowledge_hub.core.errors import DocumentNotFound, InvalidDocumentChange
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.application.commands.update_document import update_document
from knowledge_hub.modules.documents.domain.commands import DocumentMutation, UpdateDocumentCommand
from knowledge_hub.modules.documents.domain.document import Document, DocumentDetail, DocumentStatus

OLD = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 2, 0, 0, 0, 123456, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class MemoryStore:
    def __init__(self, status: DocumentStatus = DocumentStatus.DRAFT) -> None:
        self.detail = DocumentDetail(
            document=Document(
                id=DocumentId("101"),
                title="Original",
                summary="old summary",
                category_id="12",
                status=status,
                word_count=2,
                publish_time=OLD if status != 0 else None,
                created_at=OLD,
                updated_at=OLD,
            ),
            content="old body",
        )
        self.provided = frozenset()

    async def mutate(
        self, document_id: DocumentId, transform: Callable[[DocumentDetail], DocumentMutation]
    ) -> DocumentDetail:
        if document_id != self.detail.document.id:
            raise DocumentNotFound(document_id)
        mutation = transform(self.detail)
        self.detail, self.provided = mutation.target, mutation.provided_fields
        return self.detail


async def test_explicit_same_and_empty_content_reach_persistence_as_provided() -> None:
    store = MemoryStore()
    for content, words in [("old body", 2), ("", 0), ("知识库 hello world", 5)]:
        saved = await update_document(
            DocumentId("101"),
            UpdateDocumentCommand(changes={"content": content}),
            store=store,
            clock=FixedClock(),
        )
        assert saved.content == content and saved.document.word_count == words
        assert store.provided == frozenset({"content"})
        assert saved.document.summary == "old summary"


async def test_missing_fields_survive_and_explicit_null_clears_optional_metadata() -> None:
    store = MemoryStore()
    saved = await update_document(
        DocumentId("101"),
        UpdateDocumentCommand(changes={"summary": None, "category_id": None}),
        store=store,
        clock=FixedClock(),
    )
    assert saved.document.summary is None and saved.document.category_id is None
    assert saved.content == "old body" and saved.document.title == "Original"
    assert store.provided == frozenset({"summary", "category_id"})


async def test_empty_patch_preserves_metadata_and_timestamp() -> None:
    store = MemoryStore()
    before = store.detail
    result = await update_document(
        DocumentId("101"), UpdateDocumentCommand(changes={}), store=store, clock=FixedClock()
    )
    assert result == before and store.provided == frozenset()


@pytest.mark.parametrize(
    ("old_status", "new_status", "published"),
    [
        (0, 1, NOW.replace(microsecond=123000)),
        (1, 1, OLD),
        (1, 2, OLD),
        (2, 1, NOW.replace(microsecond=123000)),
        (0, 2, None),
    ],
)
async def test_status_transition_uses_legacy_publish_time(
    old_status, new_status, published
) -> None:
    saved = await update_document(
        DocumentId("101"),
        UpdateDocumentCommand(changes={"status": new_status}),
        store=MemoryStore(DocumentStatus(old_status)),
        clock=FixedClock(),
    )
    assert saved.document.status == new_status and saved.document.publish_time == published


async def test_external_bigint_text_is_not_python_normalized() -> None:
    saved = await update_document(
        DocumentId("101"),
        UpdateDocumentCommand(changes={"author_id": "0x10"}),
        store=MemoryStore(),
        clock=FixedClock(),
    )
    assert saved.document.author_id == "0x10"


@pytest.mark.parametrize("field", ["title", "content", "status", "is_public"])
async def test_nonnullable_null_does_not_report_success(field: str) -> None:
    with pytest.raises(InvalidDocumentChange):
        await update_document(
            DocumentId("101"),
            UpdateDocumentCommand(changes={field: None}),
            store=MemoryStore(),
            clock=FixedClock(),
        )


async def test_missing_update_preserves_original_not_found() -> None:
    with pytest.raises(DocumentNotFound, match="Document 404 not found"):
        await update_document(
            DocumentId("404"),
            UpdateDocumentCommand(changes={"title": "new"}),
            store=MemoryStore(),
            clock=FixedClock(),
        )
