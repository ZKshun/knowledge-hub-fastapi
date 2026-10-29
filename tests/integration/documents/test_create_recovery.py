from dataclasses import replace

import pytest
from pymongo.errors import DuplicateKeyError, OperationFailure
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from knowledge_hub.core.errors import (
    ApplicationError,
    DocumentAlreadyExists,
    DocumentOperationPending,
)
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure import write_coordinator as writes
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from knowledge_hub.modules.documents.infrastructure.operation_row import OperationRow
from tests.integration.documents.conftest import Databases
from tests.integration.documents.create_support import ProcessStopped, draft


async def test_create_persists_linked_document_and_completed_journal(storage: Databases) -> None:
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    saved = await store.create(draft())
    assert saved.document.content_id is not None
    assert saved.document.summary is None
    loaded = await PostgresMongoDocumentStore(storage.postgres, storage.collection).get(
        DocumentId("101")
    )
    assert loaded == saved
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and str(raw["_id"]) == saved.document.content_id
    assert raw["contentSummary"] == "知识库 hello world" and raw["version"] == 1
    async with storage.postgres.sessions() as session:
        row = await session.scalar(select(OperationRow))
        assert row is not None and row.state == "completed"
        assert row.snapshot == {"content_id": saved.document.content_id}
        assert raw["operationId"] == row.operation_id


async def test_empty_content_keeps_legacy_mongoose_create_failure(storage: Databases) -> None:
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    with pytest.raises(ApplicationError):
        await store.create(replace(draft(), content=""))
    assert await store.get(DocumentId("101")) is None
    assert await storage.collection.count_documents({"deleted": False}) == 0


async def test_sql_failure_clears_body_and_leaves_a_nonpublic_creation_fence(
    storage: Databases,
) -> None:
    invalid = replace(draft(), document=replace(draft().document, category_id="not-a-bigint"))
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    with pytest.raises(DBAPIError):
        await store.create(invalid)
    assert await store.get(DocumentId("101")) is None
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and raw["deleted"] is True and raw["content"] == ""
    assert raw["creationFence"] is True
    assert await store.journal.list_pending() == []
    with pytest.raises(DocumentAlreadyExists):
        await store.create(draft())


async def test_duplicate_create_does_not_damage_previous_document(storage: Databases) -> None:
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    saved = await store.create(draft())
    with pytest.raises(DocumentAlreadyExists):
        await store.create(replace(draft(), content="different"))
    assert await store.get(DocumentId("101")) == saved
    assert await storage.collection.count_documents({"documentId": "101"}) == 1


async def test_mongo_failure_does_not_leave_metadata(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fail_insert(*args, **kwargs):
        raise OperationFailure("synthetic insert failure")

    monkeypatch.setattr(storage.collection, "insert_one", fail_insert)
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    with pytest.raises(OperationFailure):
        await store.create(draft())
    assert await store.get(DocumentId("101")) is None
    assert await store.journal.list_pending() == []


@pytest.mark.parametrize("phase", ["before_mongo", "after_mongo", "before_commit", "after_commit"])
async def test_restart_recovers_each_creation_boundary(
    storage: Databases, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    insert = storage.collection.insert_one
    commit = writes.commit_business

    async def stopped_insert(*args, **kwargs):
        if phase == "after_mongo":
            await insert(*args, **kwargs)
        raise ProcessStopped()

    async def stopped_commit(session):
        if phase == "after_commit":
            await commit(session)
        raise ProcessStopped()

    if "mongo" in phase:
        monkeypatch.setattr(storage.collection, "insert_one", stopped_insert)
    else:
        monkeypatch.setattr(writes, "commit_business", stopped_commit)
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    with pytest.raises(ProcessStopped):
        await store.create(draft())
    restarted = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    report = await restarted.recover_pending()
    assert report.failed == 0
    raw = await storage.collection.find_one({"documentId": "101"})
    if phase == "after_commit":
        assert report.compensated == 0
        assert raw is not None and raw["content"] == "知识库 hello world" and not raw["deleted"]
        assert await restarted.get(DocumentId("101")) is not None
    else:
        assert report.compensated == 1
        assert raw is not None and raw["deleted"] and raw["content"] == ""
        assert await restarted.get(DocumentId("101")) is None
    again = await restarted.recover_pending()
    assert (again.completed, again.compensated, again.failed) == (0, 0, 0)


async def test_commit_response_loss_never_deletes_successful_body(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit = writes.commit_business

    async def reply_lost(session):
        await commit(session)
        raise ConnectionError("commit succeeded, reply lost")

    monkeypatch.setattr(writes, "commit_business", reply_lost)
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    with pytest.raises(ConnectionError):
        await store.create(draft())
    detail = await PostgresMongoDocumentStore(storage.postgres, storage.collection).get(
        DocumentId("101")
    )
    assert detail is not None and detail.content == "知识库 hello world"
    raw = await storage.collection.find_one({"documentId": "101"})
    assert raw is not None and not raw["deleted"] and raw["version"] == 1


async def test_failed_compensation_stays_pending_blocks_writes_and_can_retry(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def sql_failure(session):
        raise RuntimeError("synthetic sql failure")

    async def compensation_failure(*args, **kwargs):
        raise OperationFailure("private text must not enter last_error")

    monkeypatch.setattr(writes, "commit_business", sql_failure)
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "replace_one", compensation_failure)
        with pytest.raises(RuntimeError):
            await store.create(draft())
    pending = await store.journal.list_pending()
    assert len(pending) == 1 and pending[0].state == "compensation_pending"
    assert pending[0].last_error == "OperationFailure"
    with pytest.raises(DocumentOperationPending):
        await store.create(draft())
    report = await PostgresMongoDocumentStore(
        storage.postgres, storage.collection
    ).recover_pending()
    assert report.compensated == 1 and report.failed == 0


async def test_tombstone_rejects_late_insert_after_recovery(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = []

    async def paused_insert(record):
        captured.append(record)
        raise ProcessStopped()

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "insert_one", paused_insert)
        with pytest.raises(ProcessStopped):
            await PostgresMongoDocumentStore(storage.postgres, storage.collection).create(draft())
    recovered = await PostgresMongoDocumentStore(
        storage.postgres, storage.collection
    ).recover_pending()
    assert recovered.compensated == 1
    with pytest.raises(DuplicateKeyError):
        await storage.collection.insert_one(captured[0])
    assert await storage.collection.count_documents({"deleted": False}) == 0
