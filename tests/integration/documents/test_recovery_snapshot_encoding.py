from dataclasses import replace

import pytest

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure import write_coordinator as writes
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from tests.integration.documents.conftest import Databases
from tests.integration.documents.create_support import draft
from tests.integration.documents.mutation_support import change


@pytest.mark.parametrize("kind", ["content", "summary", "delete"])
async def test_nul_in_existing_bson_body_does_not_prevent_successful_mutation(
    storage: Databases,
    kind: str,
) -> None:
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    await store.create(replace(draft(), content="old\x00body"))
    if kind == "delete":
        await store.soft_delete(DocumentId("101"))
    else:
        saved = await change(
            store, {"content": "new body"} if kind == "content" else {"summary": "new summary"}
        )
        assert saved.content == ("new body" if kind == "content" else "old\x00body")
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["version"] == (2 if kind == "content" else 1)
    assert raw["content"] == ("new body" if kind == "content" else "old\x00body")
    assert raw["deleted"] == (kind == "delete")


@pytest.mark.parametrize("old_summary", [None, "", "preview\x00body", "知识库🧠"])
async def test_nul_in_old_content_and_summary_survives_real_rollback_compensation(
    storage: Databases, monkeypatch: pytest.MonkeyPatch, old_summary: str | None
) -> None:
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    await store.create(replace(draft(), content="old\x00body"))
    await storage.collection.update_one(
        {"documentId": "101"}, {"$set": {"contentSummary": old_summary}}
    )

    async def failed_commit(session):
        raise RuntimeError("force rollback after Mongo")

    with monkeypatch.context() as patch:
        patch.setattr(writes, "commit_business", failed_commit)
        with pytest.raises(RuntimeError, match="force rollback after Mongo"):
            await change(store)
    assert not await store.journal.has_pending(DocumentId("101"))
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["content"] == "old\x00body"
    assert raw["contentSummary"] == old_summary and raw["version"] == 1
