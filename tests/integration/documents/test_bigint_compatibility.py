import asyncio
from dataclasses import replace

import pytest
from sqlalchemy.exc import DBAPIError

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.domain.commands import DocumentQuery
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from tests.integration.documents.conftest import Databases
from tests.integration.documents.create_support import draft
from tests.integration.documents.test_document_lock import wait_for_blocked_lock


@pytest.mark.parametrize(
    ("supplied", "expected"),
    [
        ("0x10", "16"),
        ("0o10", "8"),
        ("0b10", "2"),
        ("9223372036854775807", "9223372036854775807"),
        ("-9223372036854775808", "-9223372036854775808"),
    ],
)
async def test_foreign_bigint_strings_use_original_postgres_parser(
    storage: Databases, supplied: str, expected: str
) -> None:
    document = replace(
        draft().document,
        category_id=supplied,
        team_id=supplied,
        author_id=supplied,
        create_by=supplied,
        update_by=supplied,
    )
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    await store.create(replace(draft(), document=document))
    loaded = await store.get(DocumentId("101"))
    assert loaded is not None
    assert (
        loaded.document.category_id,
        loaded.document.team_id,
        loaded.document.author_id,
        loaded.document.create_by,
        loaded.document.update_by,
    ) == (expected,) * 5


@pytest.mark.parametrize(
    "supplied", ["１２", "١٢", "\u00a012\u00a0", "9223372036854775808", "-9223372036854775809"]
)
async def test_postgres_rejected_foreign_id_does_not_create_another_association(
    storage: Databases, supplied: str
) -> None:
    document = replace(draft().document, category_id=supplied)
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    with pytest.raises(DBAPIError):
        await store.create(replace(draft(), document=document))
    assert await store.get(DocumentId("101")) is None
    assert await storage.collection.count_documents({"deleted": False}) == 0
    assert await store.journal.list_pending() == []


async def test_route_and_query_identifiers_follow_same_postgres_rules(storage: Databases) -> None:
    document = replace(draft("16").document, category_id="16")
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    await store.create(replace(draft("16"), document=document))
    detail = await store.get(DocumentId("0x10"))
    assert detail is not None and detail.document.id == "16"
    page = await store.page(DocumentQuery(category_id="0x10"))
    assert page.total == 1 and page.items[0].id == "16"
    with pytest.raises(DBAPIError):
        await store.get(DocumentId("１６"))
    with pytest.raises(DBAPIError):
        await store.page(DocumentQuery(category_id="１６"))


async def test_equivalent_identifier_spellings_share_the_same_session_lock(
    storage: Databases,
) -> None:
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    async with store.lock.acquire(DocumentId("16")):
        task = asyncio.create_task(store.get(DocumentId("0x10")))
        try:
            await wait_for_blocked_lock(storage, 16)
            assert not task.done()
        except BaseException:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise
    assert await asyncio.wait_for(task, 2) is None
