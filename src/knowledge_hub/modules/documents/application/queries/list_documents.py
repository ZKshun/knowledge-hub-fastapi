from knowledge_hub.modules.documents.application.ports import DocumentStore
from knowledge_hub.modules.documents.domain.commands import DocumentQuery
from knowledge_hub.modules.documents.domain.document import DocumentPage


async def list_documents(query: DocumentQuery, *, store: DocumentStore) -> DocumentPage:
    return await store.page(query)
