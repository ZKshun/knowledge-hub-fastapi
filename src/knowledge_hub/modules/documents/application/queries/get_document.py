from knowledge_hub.core.errors import DocumentNotFound
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.application.ports import DocumentStore
from knowledge_hub.modules.documents.domain.document import DocumentDetail


async def get_document(document_id: DocumentId, *, store: DocumentStore) -> DocumentDetail:
    detail = await store.get(document_id)
    if detail is None:
        raise DocumentNotFound(document_id)
    return detail
