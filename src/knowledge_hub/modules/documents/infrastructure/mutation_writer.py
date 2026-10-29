from collections.abc import Awaitable, Callable

from pymongo.asynchronous.collection import AsyncCollection
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_hub.core.errors import DocumentNotFound, DocumentOperationPending
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.integrations.postgres.database import PostgresDatabase
from knowledge_hub.modules.documents.domain.document import DocumentDetail
from knowledge_hub.modules.documents.infrastructure.content_mutations import ContentMutations
from knowledge_hub.modules.documents.infrastructure.content_record import (
    ContentSnapshot,
    DocumentContentRecord,
)
from knowledge_hub.modules.documents.infrastructure.content_repository import ContentRepository
from knowledge_hub.modules.documents.infrastructure.document_lock import DocumentLock
from knowledge_hub.modules.documents.infrastructure.mappers import to_row
from knowledge_hub.modules.documents.infrastructure.metadata_repository import MetadataRepository
from knowledge_hub.modules.documents.infrastructure.mutation_plan import MutationPlan
from knowledge_hub.modules.documents.infrastructure.operation_journal import OperationJournal
from knowledge_hub.modules.documents.infrastructure.recovery import RecoveryService
from knowledge_hub.modules.documents.infrastructure.transaction_fence import lock_operation

type BuildMutation = Callable[[DocumentDetail, ContentSnapshot | None], MutationPlan]
type Commit = Callable[[AsyncSession], Awaitable[None]]


class MutationWriter:
    def __init__(
        self, postgres: PostgresDatabase, collection: AsyncCollection[DocumentContentRecord]
    ) -> None:
        self.postgres = postgres
        self.contents = ContentRepository(collection)
        self.mutations = ContentMutations(collection)
        self.metadata = MetadataRepository()
        self.journal = OperationJournal(postgres.sessions)
        self.lock = DocumentLock(postgres.lock_engine)
        self.recovery = RecoveryService(postgres, collection)

    async def run(
        self, document_id: DocumentId, build: BuildMutation, *, commit: Commit
    ) -> DocumentDetail:
        plan, prepared = None, False
        try:
            async with self.lock.acquire(document_id):
                if await self.journal.has_pending(document_id):
                    raise DocumentOperationPending(document_id)
                async with self.postgres.sessions() as session:
                    document = await self.metadata.get(session, document_id)
                if document is None:
                    raise DocumentNotFound(document_id)
                body = (
                    await self.contents.get(document.content_id, include_deleted=True)
                    if document.content_id
                    else None
                )
                current = DocumentDetail(
                    document=document, content=body.content if body and not body.deleted else ""
                )
                plan = build(current, body)
                await self.journal.prepare(plan.operation)
                prepared = True
                await self._execute(plan, commit)
                return plan.detail
        except Exception:
            if prepared and plan is not None:
                await self.recovery.recover_one(plan.operation.operation_id)
            raise

    async def _execute(self, plan: MutationPlan, commit: Commit) -> None:
        async with self.postgres.sessions() as session:
            try:
                row = await lock_operation(session, plan.operation.operation_id)
                if row is None or row.state != "prepared":
                    raise DocumentOperationPending(plan.operation.document_id)
                await self.mutations.apply(plan)
                await session.merge(to_row(plan.detail.document))
                await self.journal.mark_completed(session, plan.operation.operation_id)
                await commit(session)
            except BaseException:
                await session.invalidate()
                raise
