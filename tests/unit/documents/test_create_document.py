from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.application.commands.create_document import create_document
from knowledge_hub.modules.documents.domain.commands import CreateDocumentCommand
from knowledge_hub.modules.documents.domain.document import DocumentDetail, DocumentStatus

NOW = datetime(2026, 1, 1, 2, 3, 4, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class FixedIds:
    def next_id(self) -> DocumentId:
        return DocumentId("9007199254740993")


class SavingStore:
    draft: DocumentDetail | None = None

    async def create(self, draft: DocumentDetail) -> DocumentDetail:
        self.draft = draft
        return replace(draft, document=replace(draft.document, content_id="abc123"))


async def test_create_defaults_without_inventing_postgres_summary() -> None:
    store = SavingStore()
    saved = await create_document(
        CreateDocumentCommand(title="Title", content="知识库 hello world"),
        store=store,
        ids=FixedIds(),
        clock=FixedClock(),
    )
    assert store.draft is not None
    document = saved.document
    assert document.id == "9007199254740993" and document.content_id == "abc123"
    assert document.status == 0 and document.is_public is False
    assert document.summary is None and document.publish_time is None
    assert document.word_count == 5 and document.deleted is False
    assert document.created_at == document.updated_at == NOW
    assert (
        document.view_count
        == document.like_count
        == document.comment_count
        == document.favourite_count
        == 0
    )


@pytest.mark.parametrize(
    "status", [DocumentStatus.DRAFT, DocumentStatus.PUBLISHED, DocumentStatus.ARCHIVED]
)
async def test_create_preserves_optional_metadata_and_publication_time(
    status: DocumentStatus,
) -> None:
    saved = await create_document(
        CreateDocumentCommand(
            title="Full",
            content="body",
            summary="",
            category_id="12",
            team_id="13",
            author_id="14",
            create_by="15",
            tags="a,b",
            cover_image="https://example.invalid/c.png",
            remark="test",
            status=status,
            is_public=True,
        ),
        store=SavingStore(),
        ids=FixedIds(),
        clock=FixedClock(),
    )
    doc = saved.document
    assert (doc.category_id, doc.team_id, doc.author_id) == ("12", "13", "14")
    assert doc.create_by == doc.update_by == "15"
    assert doc.summary == "" and doc.tags == "a,b" and doc.remark == "test"
    assert doc.status == status and doc.is_public is True
    assert doc.publish_time == (NOW if status == 1 else None)


async def test_explicit_null_defaults_preserve_legacy_creation_semantics() -> None:
    saved = await create_document(
        CreateDocumentCommand(title="T", content="B", status=None, is_public=None),
        store=SavingStore(),
        ids=FixedIds(),
        clock=FixedClock(),
    )
    assert saved.document.status == 0 and saved.document.is_public is False


async def test_publication_uses_javascript_date_millisecond_precision() -> None:
    class PreciseClock:
        def now(self) -> datetime:
            return NOW + timedelta(microseconds=123456)

    saved = await create_document(
        CreateDocumentCommand(title="T", content="B", status=DocumentStatus.PUBLISHED),
        store=SavingStore(),
        ids=FixedIds(),
        clock=PreciseClock(),
    )
    assert saved.document.publish_time == datetime(2026, 1, 1, 2, 3, 4, 123000, tzinfo=UTC)


async def test_store_failure_is_not_reported_as_success() -> None:
    class FailingStore(SavingStore):
        async def create(self, draft: DocumentDetail) -> DocumentDetail:
            raise RuntimeError("write failed")

    with pytest.raises(RuntimeError, match="write failed"):
        await create_document(
            CreateDocumentCommand(title="T", content="B"),
            store=FailingStore(),
            ids=FixedIds(),
            clock=FixedClock(),
        )
