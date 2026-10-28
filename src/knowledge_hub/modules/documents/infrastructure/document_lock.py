import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from knowledge_hub.core.identifiers import DocumentId


class DocumentLock:
    def __init__(self, engine: AsyncEngine, *, timeout_ms: int = 5000) -> None:
        if type(timeout_ms) is not int or timeout_ms < 1:
            raise ValueError("timeout_ms must be a positive integer")
        self.engine, self.timeout_ms = engine, timeout_ms

    @asynccontextmanager
    async def acquire(self, document_id: DocumentId) -> AsyncIterator[None]:
        key = int(document_id)
        if not -(1 << 63) <= key < (1 << 63):
            raise ValueError("Document ID is outside the BIGINT lock key range")
        async with self.engine.connect() as connection:
            acquired = False
            try:
                await connection.execute(
                    text("SELECT set_config('lock_timeout', :value, true)"),
                    {"value": f"{self.timeout_ms}ms"},
                )
                await connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
                acquired = True
                # Session lock survives this commit and all independent business transactions.
                await connection.commit()
                yield
            finally:
                cleanup = asyncio.create_task(self._release(connection, key, acquired))
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    await cleanup
                    raise

    @staticmethod
    async def _release(connection: AsyncConnection, key: int, acquired: bool) -> None:
        if not acquired:
            # A cancelled/failed acquisition may have reached the server: never reuse its session.
            await connection.invalidate()
            return
        try:
            await connection.rollback()
            released = await connection.scalar(
                text("SELECT pg_advisory_unlock(:key)"), {"key": key}
            )
            if released is not True:
                raise RuntimeError("Document session lock was lost")
            await connection.commit()
        except BaseException:
            await connection.invalidate()
            raise
