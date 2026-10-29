from datetime import UTC, datetime

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.integrations.postgres.identifiers import bigint_parameter
from knowledge_hub.modules.documents.infrastructure.mappers import as_utc, to_operation_record
from knowledge_hub.modules.documents.infrastructure.operation_row import OperationRow
from knowledge_hub.modules.documents.infrastructure.operation_types import OperationRecord

_PENDING_STATES = ("prepared", "compensation_pending")


class OperationJournal:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def prepare(self, record: OperationRecord) -> None:
        if record.state != "prepared":
            raise ValueError("New operations must be prepared")
        async with self.sessions.begin() as session:
            session.add(
                OperationRow(
                    operation_id=record.operation_id,
                    document_id=int(record.document_id),
                    operation_type=record.operation_type,
                    state=record.state,
                    expected_version=record.expected_version,
                    snapshot=record.snapshot,
                    last_error=record.last_error,
                    created_at=as_utc(record.created_at),
                    updated_at=as_utc(record.updated_at),
                )
            )

    async def get(self, operation_id: str) -> OperationRecord | None:
        async with self.sessions() as session:
            row = await session.get(OperationRow, operation_id)
            return to_operation_record(row) if row else None

    async def has_pending(self, document_id: DocumentId) -> bool:
        async with self.sessions() as session:
            return bool(
                await session.scalar(
                    select(
                        exists().where(
                            OperationRow.document_id == bigint_parameter(document_id),
                            OperationRow.state.in_(_PENDING_STATES),
                        )
                    )
                )
            )

    async def list_pending(self, limit: int = 100) -> list[OperationRecord]:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        async with self.sessions() as session:
            rows = await session.scalars(
                select(OperationRow)
                .where(OperationRow.state.in_(_PENDING_STATES))
                .order_by(OperationRow.created_at, OperationRow.operation_id)
                .limit(limit)
            )
            return [to_operation_record(row) for row in rows]

    async def mark_completed(self, session: AsyncSession, operation_id: str) -> None:
        # Caller owns this transaction, shared with the metadata write.
        result = await session.scalar(
            update(OperationRow)
            .where(
                OperationRow.operation_id == operation_id,
                OperationRow.state.in_(_PENDING_STATES),
            )
            .values(state="completed", updated_at=datetime.now(UTC))
            .returning(OperationRow.operation_id)
        )
        if result is None:
            raise ValueError("Operation is not pending")
