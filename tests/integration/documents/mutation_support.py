from datetime import UTC, datetime

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.application.commands.update_document import update_document
from knowledge_hub.modules.documents.domain.commands import UpdateDocumentCommand
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from tests.integration.documents.conftest import Databases
from tests.integration.documents.create_support import draft


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 2, 0, 0, 0, 123456, tzinfo=UTC)


async def seeded(storage: Databases) -> PostgresMongoDocumentStore:
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    await store.create(draft())
    return store


async def change(store: PostgresMongoDocumentStore, changes=None):
    return await update_document(
        DocumentId("101"),
        UpdateDocumentCommand(changes={"content": "new body"} if changes is None else changes),
        store=store,
        clock=FixedClock(),
    )
