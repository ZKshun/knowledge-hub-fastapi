import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from knowledge_hub.core.errors import DocumentContentNotFound, DocumentNotFound
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.application.commands.delete_document import delete_document
from knowledge_hub.modules.documents.domain.commands import DocumentMutation, DocumentQuery
from knowledge_hub.modules.documents.infrastructure.document_row import DocumentRow
from tests.integration.documents.conftest import Databases
from tests.integration.documents.mutation_support import change, seeded


@pytest.mark.parametrize(
    ("changes", "content", "summary", "version", "word_count"),
    [
        ({}, "知识库 hello world", "知识库 hello world", 1, 5),
        ({"title": "Renamed"}, "知识库 hello world", "知识库 hello world", 1, 5),
        ({"summary": "manual"}, "知识库 hello world", "manual", 1, 5),
        ({"summary": None}, "知识库 hello world", None, 1, 5),
        ({"content": "知识库 hello world"}, "知识库 hello world", "知识库 hello world", 2, 5),
        ({"content": ""}, "", "", 2, 0),
        ({"content": "a 🧠", "summary": "preview"}, "a 🧠", "preview", 2, 2),
        ({"content": "a 🧠", "summary": None}, "a 🧠", "a 🧠", 2, 2),
    ],
)
async def test_patch_preserves_legacy_body_summary_version_and_metadata(
    storage: Databases, changes, content, summary, version, word_count
) -> None:
    store = await seeded(storage)
    result = await change(store, changes)
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None
    assert (raw["content"], raw["contentSummary"], raw["version"]) == (content, summary, version)
    assert raw["contentLength"] == (4 if content == "a 🧠" else (0 if content == "" else 15))
    assert result.content == content and result.document.word_count == word_count
    assert result.document.summary == changes.get("summary")
    persisted = await store.get(DocumentId("101"))
    assert persisted is not None and persisted.content == content
    assert persisted.document.word_count == word_count
    if not changes or "content" in changes and content == "知识库 hello world":
        assert persisted.document.updated_at.year == 2026
        assert persisted.document.updated_at.day == 1


async def test_soft_delete_retains_original_body_and_version_and_excludes_reads(
    storage: Databases,
) -> None:
    store = await seeded(storage)
    result = await delete_document(DocumentId("101"), store=store)
    assert result.document_id == "101" and result.deleted
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["deleted"] and raw["content"] == "知识库 hello world"
    assert raw["version"] == 1 and "creationFence" not in raw
    assert await store.get(DocumentId("101")) is None
    assert (await store.page(DocumentQuery())).total == 0
    async with storage.postgres.sessions() as session:
        row = await session.get(DocumentRow, 101)
        assert row is not None and row.deleted
    with pytest.raises(DocumentNotFound):
        await delete_document(DocumentId("101"), store=store)
    with pytest.raises(DocumentNotFound):
        await change(store)


async def test_missing_body_allows_metadata_summary_and_delete_but_not_content(
    storage: Databases,
) -> None:
    store = await seeded(storage)
    await storage.collection.delete_many({})
    with pytest.raises(DocumentContentNotFound, match="Document content .* not found"):
        await change(store)
    assert (await change(store, {"summary": "Only SQL"})).content == ""
    assert (await change(store, {"title": "Only title"})).document.title == "Only title"
    assert await storage.collection.count_documents({}) == 0
    await store.soft_delete(DocumentId("101"))
    assert await store.get(DocumentId("101")) is None


async def test_update_external_bigint_uses_postgres_parser_and_alias_route(
    storage: Databases,
) -> None:
    store = await seeded(storage)
    await store.mutate(
        DocumentId("0x65"),
        lambda current: DocumentMutation(target=current, provided_fields=frozenset()),
    )
    await change(store, {"category_id": "0x10", "team_id": "0o10", "update_by": "0b10"})
    async with storage.postgres.sessions() as session:
        row = await session.scalar(select(DocumentRow).where(DocumentRow.id == 101))
        assert row is not None
        assert (row.category_id, row.team_id, row.update_by) == (16, 8, 2)
    with pytest.raises(DBAPIError):
        await change(store, {"author_id": "１２"})
    assert not await store.journal.has_pending(DocumentId("101"))
