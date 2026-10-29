import asyncio

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from knowledge_hub.core.errors import DocumentOperationPending
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure import write_coordinator as writes
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from knowledge_hub.modules.documents.infrastructure.recovery import RecoveryService
from knowledge_hub.modules.documents.infrastructure.transaction_fence import lock_operation
from tests.integration.documents.conftest import Databases
from tests.integration.documents.create_support import ProcessStopped, draft


async def interrupted_after_mongo(storage: Databases, monkeypatch: pytest.MonkeyPatch):
    insert = storage.collection.insert_one

    async def stopped_insert(*args, **kwargs):
        await insert(*args, **kwargs)
        raise ProcessStopped()

    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "insert_one", stopped_insert)
        with pytest.raises(ProcessStopped):
            await store.create(draft())
    return (await store.journal.list_pending())[0]


async def test_active_old_transaction_prevents_compensation_even_after_new_document_lock(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    operation = await interrupted_after_mongo(storage, monkeypatch)
    async with storage.postgres.sessions() as old_transaction:
        await lock_operation(old_transaction, operation.operation_id)
        service = RecoveryService(storage.postgres, storage.collection, fence_timeout_ms=50)
        assert await service.recover_one(operation.operation_id) == "failed"
        raw = await storage.collection.find_one({"documentId": "101"})
        assert raw is not None and raw["content"] == "知识库 hello world" and not raw["deleted"]
        store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
        with pytest.raises(DocumentOperationPending):
            await store.create(draft())
        await old_transaction.rollback()
    report = await store.recover_pending()
    assert report.compensated == 1 and report.failed == 0


@pytest.mark.parametrize("committed", [False, True])
async def test_unavailable_business_postgres_leaves_mongo_until_reconciliation(
    storage: Databases, monkeypatch: pytest.MonkeyPatch, committed: bool
) -> None:
    commit = writes.commit_business
    engine = storage.postgres.engine
    unavailable = create_async_engine(
        engine.url.set(port=1), connect_args={"timeout": 0.2}, hide_parameters=True
    )

    async def connection_lost(session):
        if committed:
            await commit(session)
        storage.postgres.sessions.configure(bind=unavailable)
        raise ConnectionError("synthetic lost commit response and unavailable SQL transport")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(writes, "commit_business", connection_lost)
            with pytest.raises(ConnectionError):
                await PostgresMongoDocumentStore(storage.postgres, storage.collection).create(
                    draft()
                )
        raw = await storage.collection.find_one({"documentId": "101"})
        assert raw is not None and raw["content"] == "知识库 hello world" and not raw["deleted"]
        with pytest.raises((OSError, SQLAlchemyError)):
            await PostgresMongoDocumentStore(storage.postgres, storage.collection).create(draft())
        assert await storage.collection.count_documents({"documentId": "101"}) == 1
    finally:
        storage.postgres.sessions.configure(bind=engine)
        await unavailable.dispose()
    restarted = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    report = await restarted.recover_pending()
    assert report.failed == 0 and report.compensated == (0 if committed else 1)
    detail = await restarted.get(DocumentId("101"))
    assert (detail is not None) is committed


async def test_recovery_never_overwrites_foreign_operation_or_newer_version(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    operation = await interrupted_after_mongo(storage, monkeypatch)
    await storage.collection.update_one(
        {"documentId": "101"},
        {
            "$set": {
                "operationId": "other-operation",
                "version": 2,
                "content": "newer successful text",
            }
        },
    )
    service = RecoveryService(storage.postgres, storage.collection)
    assert await service.recover_one(operation.operation_id) == "failed"
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["content"] == "newer successful text" and raw["version"] == 2
    assert not raw["deleted"]


async def test_cancelled_create_is_recoverable_without_online_compensation(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    insert = storage.collection.insert_one
    inserted = asyncio.Event()

    async def paused_after_insert(*args, **kwargs):
        await insert(*args, **kwargs)
        inserted.set()
        await asyncio.Event().wait()

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "insert_one", paused_after_insert)
        store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
        task = asyncio.create_task(store.create(draft()))
        await asyncio.wait_for(inserted.wait(), 3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    report = await PostgresMongoDocumentStore(
        storage.postgres, storage.collection
    ).recover_pending()
    assert report.compensated == 1 and report.failed == 0
