import asyncio

import pytest

from knowledge_hub.core.errors import DocumentNotFound
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from tests.integration.documents.conftest import Databases
from tests.integration.documents.mutation_support import change, seeded
from tests.integration.documents.test_document_lock import wait_for_blocked_lock


async def test_concurrent_updates_use_latest_metadata_and_increment_each_explicit_body(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = await seeded(storage)
    second = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    entered, release, attempted = asyncio.Event(), asyncio.Event(), asyncio.Event()
    update = storage.collection.update_one

    async def paused(*args, **kwargs):
        result = await update(*args, **kwargs)
        if not entered.is_set():
            entered.set()
            await release.wait()
        return result

    async def second_update():
        attempted.set()
        return await change(second, {"content": "second body", "summary": "second summary"})

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "update_one", paused)
        task = asyncio.create_task(change(first, {"title": "first title", "content": "first body"}))
        try:
            await asyncio.wait_for(entered.wait(), 3)
            other = asyncio.create_task(second_update())
            await asyncio.wait_for(attempted.wait(), 3)
            await wait_for_blocked_lock(storage, 101)
        finally:
            release.set()
        await asyncio.wait_for(asyncio.gather(task, other), 5)
    result = await first.get(DocumentId("101"))
    assert result is not None and result.content == "second body"
    assert result.document.title == "first title" and result.document.summary == "second summary"
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["version"] == 3 and not raw["deleted"]


@pytest.mark.parametrize("delete_first", [False, True])
async def test_update_delete_race_never_revives_deleted_body(
    storage: Databases, monkeypatch: pytest.MonkeyPatch, delete_first: bool
) -> None:
    store = await seeded(storage)
    entered, release = asyncio.Event(), asyncio.Event()
    update = storage.collection.update_one

    async def paused(*args, **kwargs):
        result = await update(*args, **kwargs)
        if not entered.is_set():
            entered.set()
            await release.wait()
        return result

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "update_one", paused)
        task = asyncio.create_task(
            store.soft_delete(DocumentId("101")) if delete_first else change(store)
        )
        try:
            await asyncio.wait_for(entered.wait(), 3)
            other = asyncio.create_task(
                change(store) if delete_first else store.soft_delete(DocumentId("101"))
            )
            await wait_for_blocked_lock(storage, 101)
        finally:
            release.set()
        results = await asyncio.wait_for(asyncio.gather(task, other, return_exceptions=True), 5)
    if delete_first:
        assert isinstance(results[1], DocumentNotFound)
    else:
        assert results[1] is None
    assert await store.get(DocumentId("101")) is None
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["deleted"] and raw["version"] == (1 if delete_first else 2)


async def test_cancelled_mutation_restarts_and_restores_without_version_growth(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = await seeded(storage)
    update, entered = storage.collection.update_one, asyncio.Event()

    async def paused(*args, **kwargs):
        result = await update(*args, **kwargs)
        entered.set()
        await asyncio.Event().wait()
        return result

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "update_one", paused)
        task = asyncio.create_task(change(store))
        await asyncio.wait_for(entered.wait(), 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    restarted = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    assert (await restarted.recover_pending()).compensated == 1
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["version"] == 1 and raw["content"] == "知识库 hello world"


async def test_old_completed_update_recovery_after_successful_delete_cannot_resurrect(
    storage: Databases,
) -> None:
    store = await seeded(storage)
    await change(store)
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None
    operation_id = raw["operationId"]
    await store.soft_delete(DocumentId("101"))
    assert await store.recovery.recover_one(operation_id) == "completed"
    after = await storage.collection.find_one({"documentId": "101"})
    assert after is not None and after["deleted"] and after["content"] == "new body"


async def test_recovery_handles_legacy_body_without_operation_marker(storage: Databases) -> None:
    store = await seeded(storage)
    await storage.collection.update_one({"documentId": "101"}, {"$unset": {"operationId": ""}})
    await change(store, {"content": "legacy changed"})
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["version"] == 2 and raw["content"] == "legacy changed"
