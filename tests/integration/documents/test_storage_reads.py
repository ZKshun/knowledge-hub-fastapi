import asyncio
from dataclasses import asdict
from datetime import UTC, datetime

import pytest
from bson import ObjectId
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError
from sqlalchemy import text

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.domain.commands import DocumentQuery
from knowledge_hub.modules.documents.infrastructure.content_repository import ContentRepository
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from knowledge_hub.modules.documents.infrastructure.mappers import make_content_record
from scripts.init_mongo_indexes import initialize_indexes
from scripts.legacy_v1.runner import MONGO_URI
from tests.integration.documents.conftest import Databases


async def seed(storage: Databases) -> None:
    async with storage.postgres.engine.begin() as connection:
        for number, title, deleted in [
            (1, "Alpha 知识库", False),
            (2, "alpha second", False),
            (3, "ALPHA", True),
        ]:
            oid = ObjectId(f"00000000000000000000000{number}")
            await storage.collection.insert_one(
                {
                    "_id": oid,
                    "documentId": str(number),
                    "content": f"正文 {number}",
                    "contentLength": 4,
                    "contentSummary": "正文",
                    "version": 1,
                    "deleted": False,
                    "createdAt": datetime(2026, 1, 1, tzinfo=UTC),
                    "updatedAt": datetime(2026, 1, 1, tzinfo=UTC),
                }
            )
            await connection.execute(
                text("""
                INSERT INTO kh_document(id,title,content_id,category_id,team_id,author_id,
                    create_by,update_by,status,created_at,updated_at,deleted)
                VALUES(:id,:title,:content_id,9007199254740993,9007199254740994,
                    9007199254740995,9007199254740996,9007199254740996,0,
                    :created_at,:created_at,:deleted)
                """),
                dict(
                    id=number,
                    title=title,
                    content_id=str(oid),
                    created_at=datetime(2026, 1, number),
                    deleted=deleted,
                ),
            )


async def test_detail_maps_legacy_object_id_bigints_nulls_and_utc(storage: Databases) -> None:
    await seed(storage)
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    detail = await store.get(DocumentId("1"))
    assert detail is not None and detail.content == "正文 1"
    assert detail.document.id == "1"
    assert detail.document.content_id == "000000000000000000000001"
    assert detail.document.category_id == "9007199254740993"
    assert detail.document.team_id == "9007199254740994"
    assert detail.document.author_id == "9007199254740995"
    assert detail.document.create_by == detail.document.update_by == "9007199254740996"
    assert detail.document.summary is None and detail.document.publish_time is None
    assert detail.document.created_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert await store.get(DocumentId("3")) is None
    assert await store.get(DocumentId("999")) is None


async def test_parallel_details_do_not_starve_business_connections(storage: Databases) -> None:
    await seed(storage)
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    async with asyncio.timeout(3):
        results = await asyncio.gather(
            *(store.get(DocumentId(str(number))) for number in range(1, 21))
        )
    assert results[0] is not None and results[0].content == "正文 1"
    assert results[1] is not None and results[1].content == "正文 2"
    assert all(detail is None for detail in results[2:])


async def test_page_filters_orders_and_counts_without_fetching_content(storage: Databases) -> None:
    await seed(storage)
    closed = AsyncMongoClient(MONGO_URI)
    collection = closed.get_default_database().get_collection(storage.collection.name)
    await closed.close()
    store = PostgresMongoDocumentStore(storage.postgres, collection)
    query = DocumentQuery(
        title="ALpHa",
        category_id="9007199254740993",
        team_id="9007199254740994",
        author_id="9007199254740995",
        status=0,
        page_size=1,
        page=2,
    )
    page = await store.page(query)
    assert (page.total, page.page, page.page_size) == (2, 2, 1)
    assert [doc.id for doc in page.items] == ["1"]
    assert "content" not in asdict(page.items[0])
    assert (await store.page(DocumentQuery(status=999))).total == 0
    assert (await store.page(DocumentQuery(title="%"))).total == 2
    assert (await store.page(DocumentQuery(title="' OR true --"))).total == 0
    assert (await store.page(DocumentQuery(category_id="0"))).total == 0


@pytest.mark.parametrize("missing", ["absent", "deleted"])
async def test_missing_or_soft_deleted_content_returns_empty(
    storage: Databases, missing: str
) -> None:
    await seed(storage)
    if missing == "absent":
        await storage.collection.delete_one({"documentId": "1"})
    else:
        await storage.collection.update_one({"documentId": "1"}, {"$set": {"deleted": True}})
    detail = await PostgresMongoDocumentStore(storage.postgres, storage.collection).get(
        DocumentId("1")
    )
    assert detail is not None and detail.content == ""


async def test_bson_summary_encoding_matches_captured_legacy_boundary(storage: Databases) -> None:
    import json
    from pathlib import Path

    evidence = json.loads(
        (
            Path(__file__).parents[2] / "fixtures/contracts/v1/044_create_unicode_boundary.json"
        ).read_text()
    )
    content = evidence["request"]["body"]["content"]
    record = make_content_record(DocumentId("123"), content, now=datetime(2026, 1, 1, tzinfo=UTC))
    await storage.collection.insert_one(record)
    snapshot = await ContentRepository(storage.collection).get(str(record["_id"]))
    original = next(
        doc
        for doc in evidence["state"]["mongo"]
        if doc["documentId"] == evidence["response"]["body"]["id"]
    )
    assert snapshot is not None
    assert snapshot.content_summary == original["contentSummary"] == "a" * 199 + "\ufffd..."
    assert snapshot.content_length == 206 and snapshot.version == 1


async def test_indexes_are_idempotent_and_preserve_original_unique_constraint(
    storage: Databases,
) -> None:
    await initialize_indexes(storage.collection)
    await initialize_indexes(storage.collection)
    await seed(storage)
    with pytest.raises(DuplicateKeyError):
        await storage.collection.insert_one(
            make_content_record(DocumentId("1"), "duplicate", now=datetime(2026, 1, 1, tzinfo=UTC))
        )
    indexes = await storage.collection.index_information()
    assert indexes["documentId_1"]["unique"] is True
    assert indexes["deleted_1"]["key"] == [("deleted", 1)]
