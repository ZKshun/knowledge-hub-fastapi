from pymongo.asynchronous.collection import AsyncCollection
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_hub.core.errors import DocumentAlreadyExists, DocumentOperationPending
from knowledge_hub.integrations.postgres.database import PostgresDatabase
from knowledge_hub.modules.documents.domain.document import DocumentDetail
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord
from knowledge_hub.modules.documents.infrastructure.content_repository import ContentRepository
from knowledge_hub.modules.documents.infrastructure.document_lock import DocumentLock
from knowledge_hub.modules.documents.infrastructure.mappers import to_row
from knowledge_hub.modules.documents.infrastructure.metadata_repository import MetadataRepository
from knowledge_hub.modules.documents.infrastructure.operation_journal import OperationJournal
from knowledge_hub.modules.documents.infrastructure.recovery import RecoveryService
from knowledge_hub.modules.documents.infrastructure.transaction_fence import lock_operation
from knowledge_hub.modules.documents.infrastructure.write_create import CreationPlan, plan_creation


async def commit_business(session: AsyncSession) -> None:
    await session.commit()


class WriteCoordinator:
    def __init__(
        self, postgres: PostgresDatabase, collection: AsyncCollection[DocumentContentRecord]
    ) -> None:
        self.postgres = postgres
        self.contents = ContentRepository(collection)
        self.metadata = MetadataRepository()
        self.journal = OperationJournal(postgres.sessions)
        self.lock = DocumentLock(postgres.lock_engine)
        self.recovery = RecoveryService(postgres, collection)

    async def create(self, draft: DocumentDetail) -> DocumentDetail:
        plan = plan_creation(draft)
        prepared = False
        try:
            async with self.lock.acquire(draft.document.id):
                if await self.journal.has_pending(draft.document.id):
                    raise DocumentOperationPending(draft.document.id)
                async with self.postgres.sessions() as session:
                    exists = await self.metadata.exists(session, draft.document.id)
                if exists or await self.contents.has_document(draft.document.id):
                    raise DocumentAlreadyExists(draft.document.id)
                await self.journal.prepare(plan.operation)
                prepared = True
                await self._execute(plan)
                return plan.detail
        except Exception:
            if prepared:
                await self.recovery.recover_one(plan.operation.operation_id)
            raise

    async def _execute(self, plan: CreationPlan) -> None:
        async with self.postgres.sessions() as session:
            try:
                row = await lock_operation(session, plan.operation.operation_id)
                if row is None or row.state != "prepared":
                    raise DocumentOperationPending(plan.operation.document_id)
                await self.contents.insert_creation(plan.content)
                session.add(to_row(plan.detail.document))
                await self.journal.mark_completed(session, plan.operation.operation_id)
                await commit_business(session)
            except BaseException:
                # Never return a connection with unknown COMMIT/transaction state to the pool.
                await session.invalidate()
                raise
