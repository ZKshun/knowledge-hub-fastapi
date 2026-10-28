from datetime import UTC, datetime
from typing import Literal

from pymongo.asynchronous.collection import AsyncCollection
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_hub.core.errors import OperationRecoveryError
from knowledge_hub.integrations.postgres.database import PostgresDatabase
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord
from knowledge_hub.modules.documents.infrastructure.content_repository import ContentRepository
from knowledge_hub.modules.documents.infrastructure.document_lock import DocumentLock
from knowledge_hub.modules.documents.infrastructure.document_row import DocumentRow
from knowledge_hub.modules.documents.infrastructure.mappers import to_operation_record
from knowledge_hub.modules.documents.infrastructure.operation_journal import OperationJournal
from knowledge_hub.modules.documents.infrastructure.operation_row import OperationRow
from knowledge_hub.modules.documents.infrastructure.operation_types import RecoveryReport
from knowledge_hub.modules.documents.infrastructure.transaction_fence import lock_operation

type RecoveryOutcome = Literal["completed", "compensated", "failed"]


class RecoveryService:
    def __init__(
        self,
        postgres: PostgresDatabase,
        collection: AsyncCollection[DocumentContentRecord],
        *,
        fence_timeout_ms: int = 5000,
    ) -> None:
        if type(fence_timeout_ms) is not int or fence_timeout_ms < 1:
            raise ValueError("fence_timeout_ms must be positive")
        self.postgres = postgres
        self.contents = ContentRepository(collection)
        self.journal = OperationJournal(postgres.sessions)
        self.lock = DocumentLock(postgres.lock_engine)
        self.fence_timeout_ms = fence_timeout_ms

    async def recover_pending(self, *, limit: int = 100) -> RecoveryReport:
        pending = await self.journal.list_pending(limit)
        counts = {"completed": 0, "compensated": 0, "failed": 0}
        for operation in pending:
            counts[await self.recover_one(operation.operation_id)] += 1
        return RecoveryReport(
            completed=counts["completed"],
            compensated=counts["compensated"],
            failed=counts["failed"],
        )

    async def recover_one(self, operation_id: str) -> RecoveryOutcome:
        try:
            operation = await self.journal.get(operation_id)
            if operation is None:
                return "failed"
            async with self.lock.acquire(operation.document_id):
                try:
                    return await self._resolve(operation_id)
                except Exception as error:
                    await self._note_failure(operation_id, type(error).__name__)
                    return "failed"
        except Exception:
            # No SQL/lock proof: keep the durable operation untouched and retry later.
            return "failed"

    async def _resolve(self, operation_id: str) -> RecoveryOutcome:
        async with self.postgres.sessions() as session:
            try:
                row = await lock_operation(session, operation_id, timeout_ms=self.fence_timeout_ms)
                outcome = await self._resolve_locked(session, row)
                await session.commit()
                return outcome
            except BaseException:
                await session.invalidate()
                raise

    async def _resolve_locked(
        self, session: AsyncSession, row: OperationRow | None
    ) -> RecoveryOutcome:
        if row is None or row.operation_type != "create":
            raise OperationRecoveryError("Unsupported or missing recovery operation")
        if row.state == "compensated":
            return "compensated"
        metadata = await session.get(DocumentRow, row.document_id)
        if row.state == "completed":
            if metadata is None or metadata.content_id != row.snapshot.get("content_id"):
                raise OperationRecoveryError("Completed create metadata does not match its journal")
            return "completed"
        if metadata is not None:
            raise OperationRecoveryError("Pending create conflicts with existing metadata")
        await self.contents.compensate_creation(to_operation_record(row))
        row.state, row.last_error, row.updated_at = "compensated", None, datetime.now(UTC)
        return "compensated"

    async def _note_failure(self, operation_id: str, error_type: str) -> None:
        try:
            async with self.postgres.sessions() as session:
                try:
                    row = await lock_operation(
                        session, operation_id, timeout_ms=self.fence_timeout_ms
                    )
                    if row is not None and row.state in ("prepared", "compensation_pending"):
                        row.state = "compensation_pending"
                        row.last_error, row.updated_at = error_type[:100], datetime.now(UTC)
                    await session.commit()
                except BaseException:
                    await session.invalidate()
                    raise
        except Exception:
            # The SQL outage or active old transaction itself prevents safe status mutation.
            return
