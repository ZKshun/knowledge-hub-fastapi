from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.application.ports import DocumentStore
from knowledge_hub.modules.documents.domain.document import DeleteDocumentResult


async def delete_document(document_id: DocumentId, *, store: DocumentStore) -> DeleteDocumentResult:
    await store.soft_delete(document_id)
    return DeleteDocumentResult(document_id=document_id, deleted=True)
