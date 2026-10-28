from pymongo.asynchronous.collection import AsyncCollection

from knowledge_hub.core.errors import DocumentOperationPending
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.integrations.postgres.database import PostgresDatabase
from knowledge_hub.modules.documents.domain.commands import DocumentQuery
from knowledge_hub.modules.documents.domain.document import DocumentDetail, DocumentPage
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord
from knowledge_hub.modules.documents.infrastructure.content_repository import ContentRepository
from knowledge_hub.modules.documents.infrastructure.document_lock import DocumentLock
from knowledge_hub.modules.documents.infrastructure.metadata_repository import MetadataRepository
from knowledge_hub.modules.documents.infrastructure.operation_journal import OperationJournal
from knowledge_hub.modules.documents.infrastructure.operation_types import RecoveryReport
from knowledge_hub.modules.documents.infrastructure.recovery import RecoveryService
from knowledge_hub.modules.documents.infrastructure.write_coordinator import WriteCoordinator


class PostgresMongoDocumentStore:
    """Read and recoverable-create adapter; mutation methods arrive in Task 5."""

    def __init__(
        self, postgres: PostgresDatabase, collection: AsyncCollection[DocumentContentRecord]
    ) -> None:
        self.postgres = postgres
        self.metadata = MetadataRepository()
        self.contents = ContentRepository(collection)
        self.lock = DocumentLock(postgres.lock_engine)
        self.journal = OperationJournal(postgres.sessions)
        self.writer = WriteCoordinator(postgres, collection)
        self.recovery = RecoveryService(postgres, collection)

    async def create(self, draft: DocumentDetail) -> DocumentDetail:
        return await self.writer.create(draft)

    async def recover_pending(self, *, limit: int = 100) -> RecoveryReport:
        return await self.recovery.recover_pending(limit=limit)

    async def get(self, document_id: DocumentId) -> DocumentDetail | None:
        async with self.lock.acquire(document_id):
            if await self.journal.has_pending(document_id):
                raise DocumentOperationPending(document_id)
            async with self.postgres.sessions() as session:
                document = await self.metadata.get(session, document_id)
            if document is None:
                return None
            content = await self.contents.get(document.content_id) if document.content_id else None
            return DocumentDetail(document=document, content=content.content if content else "")

    async def page(self, query: DocumentQuery) -> DocumentPage:
        async with self.postgres.sessions() as session:
            return await self.metadata.page(session, query)
