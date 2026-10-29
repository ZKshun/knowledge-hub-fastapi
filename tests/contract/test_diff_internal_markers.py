from dataclasses import replace

import pytest
from sqlalchemy.exc import DBAPIError

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from tests.integration.documents.create_support import draft
from tests.support.v1_state import snapshot


async def test_snapshot_comparison_preserves_soft_deleted_body(storage):
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    await store.create(draft())
    await store.soft_delete(DocumentId("101"))
    state = await snapshot(storage)
    assert state["postgres"][0]["deleted"] is True
    assert len(state["mongo"]) == 1
    assert state["mongo"][0]["deleted"] is True
    assert state["mongo"][0]["content"] == "知识库 hello world"


async def test_only_verified_empty_creation_fence_may_be_excluded(storage):
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    with pytest.raises(DBAPIError):
        await store.create(
            replace(draft(), document=replace(draft().document, category_id="invalid"))
        )
    assert await snapshot(storage) == {"postgres": [], "mongo": []}
    await storage.collection.update_one(
        {"documentId": "101"}, {"$set": {"content": "must not be silently ignored"}}
    )
    with pytest.raises(AssertionError):
        await snapshot(storage)
