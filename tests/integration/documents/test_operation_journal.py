from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from knowledge_hub.core.errors import DocumentOperationPending
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from knowledge_hub.modules.documents.infrastructure.operation_journal import OperationJournal
from knowledge_hub.modules.documents.infrastructure.operation_types import OperationRecord
from tests.integration.documents.conftest import Databases


def record(document_id: str = "1") -> OperationRecord:
    return OperationRecord(
        operation_id=str(uuid4()),
        document_id=DocumentId(document_id),
        operation_type="create",
        state="prepared",
        expected_version=None,
        snapshot={"content": "synthetic private recovery data", "metadata": {"title": "test"}},
        last_error=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


async def test_prepare_is_durable_and_business_rollback_keeps_recovery_evidence(
    storage: Databases,
) -> None:
    journal = OperationJournal(storage.postgres.sessions)
    operation = record()
    await journal.prepare(operation)
    assert (
        await OperationJournal(storage.postgres.sessions).get(operation.operation_id)
    ) == operation
    with pytest.raises(RuntimeError):
        async with storage.postgres.sessions.begin() as session:
            await session.execute(
                text("INSERT INTO kh_document(id,title,content_id) VALUES(1,'x','y')")
            )
            await journal.mark_completed(session, operation.operation_id)
            raise RuntimeError("roll back business transaction")
    assert await journal.list_pending() == [operation]
    async with storage.postgres.engine.connect() as connection:
        assert await connection.scalar(text("SELECT count(*) FROM kh_document")) == 0


async def test_metadata_and_completed_become_visible_together(storage: Databases) -> None:
    journal = OperationJournal(storage.postgres.sessions)
    operation = record()
    await journal.prepare(operation)
    async with storage.postgres.sessions.begin() as session:
        await session.execute(
            text("INSERT INTO kh_document(id,title,content_id) VALUES(1,'x','y')")
        )
        await journal.mark_completed(session, operation.operation_id)
        assert await journal.list_pending() == [operation]
    assert await journal.list_pending() == []
    completed = await journal.get(operation.operation_id)
    assert completed is not None and completed.state == "completed"


async def test_pending_journal_blocks_detail_until_future_recovery(storage: Databases) -> None:
    await OperationJournal(storage.postgres.sessions).prepare(record())
    with pytest.raises(DocumentOperationPending):
        await PostgresMongoDocumentStore(storage.postgres, storage.collection).get(DocumentId("1"))


async def test_pending_limit_is_bounded_and_only_one_unresolved_operation_per_document(
    storage: Databases,
) -> None:
    journal = OperationJournal(storage.postgres.sessions)
    first, second = record("1"), record("2")
    await journal.prepare(first)
    await journal.prepare(second)
    pending = await journal.list_pending(limit=1)
    assert len(pending) == 1 and pending[0].operation_id == min(
        first.operation_id, second.operation_id
    )
    with pytest.raises(IntegrityError):
        await journal.prepare(record("1"))
    for limit in (0, -1, 1001):
        with pytest.raises(ValueError):
            await journal.list_pending(limit=limit)
