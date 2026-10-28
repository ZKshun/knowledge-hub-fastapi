import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure.document_lock import DocumentLock
from tests.integration.documents.conftest import Databases


async def wait_for_blocked_lock(storage: Databases, key: int) -> None:
    async with asyncio.timeout(3):
        while True:
            async with storage.postgres.engine.connect() as connection:
                waiting = await connection.scalar(
                    text("""
                    SELECT count(*) FROM pg_locks WHERE locktype='advisory'
                    AND classid=0 AND objid=:key AND NOT granted
                """),
                    {"key": key},
                )
            if waiting:
                return
            await asyncio.sleep(0.01)


async def test_same_document_serializes_across_independent_sql_commits(storage: Databases) -> None:
    lock = DocumentLock(storage.postgres.engine)
    entered = asyncio.Event()

    async def contender() -> None:
        async with DocumentLock(storage.postgres.engine).acquire(DocumentId("123")):
            entered.set()

    async with lock.acquire(DocumentId("123")):
        task = asyncio.create_task(contender())
        try:
            async with storage.postgres.engine.begin() as connection:
                await connection.execute(text("SELECT 1"))
            await wait_for_blocked_lock(storage, 123)
            assert not entered.is_set()
        except BaseException:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise
    await asyncio.wait_for(task, 2)
    assert entered.is_set()


async def test_different_documents_can_overlap_without_metadata_rows(storage: Databases) -> None:
    async with DocumentLock(storage.postgres.engine).acquire(DocumentId("124")):
        async with asyncio.timeout(1):
            async with DocumentLock(storage.postgres.engine).acquire(DocumentId("125")):
                pass


async def test_exception_and_holder_cancellation_release_session_lock(storage: Databases) -> None:
    lock = DocumentLock(storage.postgres.engine)
    with pytest.raises(RuntimeError, match="business failure"):
        async with lock.acquire(DocumentId("126")):
            raise RuntimeError("business failure")
    entered = asyncio.Event()

    async def holder() -> None:
        async with lock.acquire(DocumentId("126")):
            entered.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(holder())
    await asyncio.wait_for(entered.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with asyncio.timeout(1):
        async with lock.acquire(DocumentId("126")):
            pass


async def test_cancelled_waiter_does_not_leak_a_lock_or_connection(storage: Databases) -> None:
    lock = DocumentLock(storage.postgres.engine)

    async def waiter() -> None:
        async with lock.acquire(DocumentId("127")):
            pytest.fail("waiter should be cancelled before entering")

    async with lock.acquire(DocumentId("127")):
        task = asyncio.create_task(waiter())
        await wait_for_blocked_lock(storage, 127)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    async with asyncio.timeout(1):
        async with lock.acquire(DocumentId("127")):
            pass


async def test_lock_timeout_is_bounded_and_connection_is_reusable_after_failure(
    storage: Databases,
) -> None:
    async with DocumentLock(storage.postgres.engine).acquire(DocumentId("128")):
        with pytest.raises(DBAPIError):
            async with DocumentLock(storage.postgres.engine, timeout_ms=50).acquire(
                DocumentId("128")
            ):
                pytest.fail("conflicting lock must time out")
    async with asyncio.timeout(1):
        async with DocumentLock(storage.postgres.engine).acquire(DocumentId("128")):
            pass
