import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from knowledge_hub.core.errors import DocumentOperationPending
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure import write_coordinator as writes
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from knowledge_hub.modules.documents.infrastructure.recovery import RecoveryService
from knowledge_hub.modules.documents.infrastructure.transaction_fence import lock_operation
from tests.integration.documents.conftest import Databases
from tests.integration.documents.create_support import ProcessStopped
from tests.integration.documents.mutation_support import change, seeded
from tests.integration.documents.test_mutation_recovery import act


@pytest.mark.parametrize("kind", ["update", "delete"])
async def test_rollback_fence_rejects_late_cas_even_before_first_write_was_applied(
    storage: Databases, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    store = await seeded(storage)
    captured = []

    async def in_flight(selector, update, **kwargs):
        captured.append((selector, update, kwargs))
        raise ProcessStopped()

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "update_one", in_flight)
        with pytest.raises(ProcessStopped):
            await act(store, kind)
    operation = (await store.journal.list_pending())[0]
    assert (await store.recover_pending()).compensated == 1
    selector, update, kwargs = captured[0]
    assert (await storage.collection.update_one(selector, update, **kwargs)).matched_count == 0
    await change(store, {"content": "successful later body"})
    assert await store.recovery.recover_one(operation.operation_id) == "compensated"
    assert (await storage.collection.update_one(selector, update, **kwargs)).matched_count == 0
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["content"] == "successful later body" and raw["version"] == 2
    assert not raw["deleted"]


async def test_active_sql_fence_prevents_premature_mutation_compensation(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = await seeded(storage)
    update = storage.collection.update_one

    async def stopped(*args, **kwargs):
        await update(*args, **kwargs)
        raise ProcessStopped()

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "update_one", stopped)
        with pytest.raises(ProcessStopped):
            await change(store)
    operation = (await store.journal.list_pending())[0]
    async with storage.postgres.sessions() as old:
        await lock_operation(old, operation.operation_id)
        recovery = RecoveryService(storage.postgres, storage.collection, fence_timeout_ms=50)
        assert await recovery.recover_one(operation.operation_id) == "failed"
        raw = await storage.collection.find_one({"documentId": "101"})
        assert raw is not None and raw["content"] == "new body" and raw["version"] == 2
        await old.rollback()
    assert (await store.recover_pending()).compensated == 1


@pytest.mark.parametrize("kind", ["update", "delete"])
@pytest.mark.parametrize("committed", [False, True])
async def test_unavailable_sql_transport_never_guesses_mutation_result(
    storage: Databases, monkeypatch: pytest.MonkeyPatch, kind: str, committed: bool
) -> None:
    store = await seeded(storage)
    engine, commit = storage.postgres.engine, writes.commit_business
    unavailable = create_async_engine(
        engine.url.set(port=1), connect_args={"timeout": 0.2}, hide_parameters=True
    )

    async def unavailable_commit(session):
        if committed:
            await commit(session)
        storage.postgres.sessions.configure(bind=unavailable)
        raise ConnectionError("synthetic unavailable SQL transport")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(writes, "commit_business", unavailable_commit)
            with pytest.raises(ConnectionError):
                await act(store, kind)
        raw = await storage.collection.find_one({"documentId": "101"})
        assert raw is not None and raw["deleted"] == (kind == "delete")
        assert raw["version"] == (2 if kind == "update" else 1)
        with pytest.raises((OSError, SQLAlchemyError)):
            await change(store)
    finally:
        storage.postgres.sessions.configure(bind=engine)
        await unavailable.dispose()
    restarted = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    report = await restarted.recover_pending()
    assert report.failed == 0 and report.compensated == (0 if committed else 1)
    result = await restarted.get(DocumentId("101"))
    assert (result is None) == (committed and kind == "delete")


@pytest.mark.parametrize("foreign", ["marker", "version"])
async def test_pending_recovery_preserves_foreign_or_newer_body(
    storage: Databases, monkeypatch: pytest.MonkeyPatch, foreign: str
) -> None:
    store = await seeded(storage)
    update = storage.collection.update_one

    async def stopped(*args, **kwargs):
        await update(*args, **kwargs)
        raise ProcessStopped()

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "update_one", stopped)
        with pytest.raises(ProcessStopped):
            await change(store)
    fields = {"content": "successful foreign body"}
    fields.update({"operationId": "foreign"} if foreign == "marker" else {"version": 3})
    await storage.collection.update_one({"documentId": "101"}, {"$set": fields})
    assert (await store.recover_pending()).failed == 1
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["content"] == "successful foreign body"
    with pytest.raises(DocumentOperationPending):
        await change(store)


async def test_interrupted_compensation_retries_with_same_rollback_fence(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = await seeded(storage)

    async def stopped_commit(session):
        raise ProcessStopped()

    with monkeypatch.context() as patch:
        patch.setattr(writes, "commit_business", stopped_commit)
        with pytest.raises(ProcessStopped):
            await change(store)
        patch.setattr(AsyncSession, "commit", stopped_commit)
        with pytest.raises(ProcessStopped):
            await store.recover_pending()
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["version"] == 1
    fence = raw["operationId"]
    assert fence.startswith("rollback:")
    assert (await store.recover_pending()).compensated == 1
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["operationId"] == fence and raw["version"] == 1


async def test_writer_resuming_after_recovery_cannot_execute_prepared_plan(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = await seeded(storage)
    writer = store.writer.mutations
    captured = []

    async def stopped(plan, commit):
        captured.append((plan, commit))
        raise ProcessStopped()

    with monkeypatch.context() as patch:
        patch.setattr(writer, "_execute", stopped)
        with pytest.raises(ProcessStopped):
            await change(store)
    assert (await store.recover_pending()).compensated == 1
    with pytest.raises(DocumentOperationPending):
        await writer._execute(*captured[0])
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["version"] == 1 and raw["content"] == "知识库 hello world"
