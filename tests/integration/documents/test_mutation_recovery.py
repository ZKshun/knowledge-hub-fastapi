import pytest
from pymongo.errors import OperationFailure
from sqlalchemy.exc import DBAPIError

from knowledge_hub.core.errors import DocumentOperationPending
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure import write_coordinator as writes
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from tests.integration.documents.conftest import Databases
from tests.integration.documents.create_support import ProcessStopped
from tests.integration.documents.mutation_support import change, seeded


async def act(store, kind):
    if kind == "delete":
        await store.soft_delete(DocumentId("101"))
    else:
        await change(store)


@pytest.mark.parametrize("kind", ["update", "delete"])
@pytest.mark.parametrize("phase", ["before_mongo", "after_mongo", "before_commit", "after_commit"])
async def test_restart_resolves_each_mutation_boundary_without_double_version_or_resurrection(
    storage: Databases, monkeypatch: pytest.MonkeyPatch, kind: str, phase: str
) -> None:
    store = await seeded(storage)
    update, commit = storage.collection.update_one, writes.commit_business

    async def stopped_update(*args, **kwargs):
        if phase == "after_mongo":
            await update(*args, **kwargs)
        raise ProcessStopped()

    async def stopped_commit(session):
        if phase == "after_commit":
            await commit(session)
        raise ProcessStopped()

    with monkeypatch.context() as patch:
        if "mongo" in phase:
            patch.setattr(storage.collection, "update_one", stopped_update)
        else:
            patch.setattr(writes, "commit_business", stopped_commit)
        with pytest.raises(ProcessStopped):
            await act(store, kind)
    restarted = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    report = await restarted.recover_pending()
    assert report.failed == 0 and report.compensated == (0 if phase == "after_commit" else 1)
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None
    committed = phase == "after_commit"
    assert raw["content"] == (
        "new body" if committed and kind == "update" else "知识库 hello world"
    )
    assert raw["version"] == (2 if committed and kind == "update" else 1)
    assert raw["deleted"] == (committed and kind == "delete")
    detail = await restarted.get(DocumentId("101"))
    assert (detail is None) == (committed and kind == "delete")
    again = await restarted.recover_pending()
    assert (again.completed, again.compensated, again.failed) == (0, 0, 0)


async def test_real_sql_constraint_rollback_restores_body_summary_version(
    storage: Databases,
) -> None:
    store = await seeded(storage)
    with pytest.raises(DBAPIError):
        await change(
            store, {"content": "should roll back", "summary": "private", "category_id": "bad"}
        )
    detail = await store.get(DocumentId("101"))
    assert detail is not None and detail.content == "知识库 hello world"
    assert detail.document.summary is None and detail.document.category_id is None
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["version"] == 1 and raw["contentSummary"] == "知识库 hello world"


@pytest.mark.parametrize("kind", ["update", "delete"])
async def test_commit_reply_loss_keeps_committed_mutation(
    storage: Databases, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    store = await seeded(storage)
    commit = writes.commit_business

    async def reply_lost(session):
        await commit(session)
        raise ConnectionError("synthetic commit reply loss")

    with monkeypatch.context() as patch:
        patch.setattr(writes, "commit_business", reply_lost)
        with pytest.raises(ConnectionError):
            await act(store, kind)
    assert not await store.journal.has_pending(DocumentId("101"))
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["deleted"] == (kind == "delete")
    assert raw["version"] == (2 if kind == "update" else 1)


@pytest.mark.parametrize("kind", ["update", "delete"])
async def test_mongo_write_failure_is_compensated_before_next_write(
    storage: Databases, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    store = await seeded(storage)

    async def rejected(*args, **kwargs):
        raise OperationFailure("synthetic write rejected")

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "update_one", rejected)
        with pytest.raises(OperationFailure):
            await act(store, kind)
    assert not await store.journal.has_pending(DocumentId("101"))
    assert (await change(store)).content == "new body"


async def test_compensation_failure_is_sanitized_and_blocks_reads_update_delete(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = await seeded(storage)

    async def failed_commit(session):
        raise RuntimeError("synthetic SQL failure")

    async def failed_compensation(*args, **kwargs):
        raise OperationFailure("private recovery text must not leak")

    with monkeypatch.context() as patch:
        patch.setattr(writes, "commit_business", failed_commit)
        patch.setattr(storage.collection, "find_one_and_update", failed_compensation)
        with pytest.raises(RuntimeError):
            await change(store)
    pending = await store.journal.list_pending()
    assert len(pending) == 1 and pending[0].state == "compensation_pending"
    assert pending[0].last_error == "OperationFailure"
    for action in (
        lambda: store.get(DocumentId("101")),
        lambda: change(store),
        lambda: store.soft_delete(DocumentId("101")),
    ):
        with pytest.raises(DocumentOperationPending):
            await action()
    report = await store.recover_pending()
    assert report.compensated == 1 and report.failed == 0
