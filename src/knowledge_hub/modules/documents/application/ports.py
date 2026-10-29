from collections.abc import Callable
from typing import Protocol

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.domain.commands import DocumentMutation, DocumentQuery
from knowledge_hub.modules.documents.domain.document import DocumentDetail, DocumentPage


class DocumentStore(Protocol):
    """Storage boundary; mutate must read and transform under the same document lock."""

    async def get(self, document_id: DocumentId) -> DocumentDetail | None: ...

    async def page(self, query: DocumentQuery) -> DocumentPage: ...

    async def create(self, draft: DocumentDetail) -> DocumentDetail: ...

    async def mutate(
        self, document_id: DocumentId, transform: Callable[[DocumentDetail], DocumentMutation]
    ) -> DocumentDetail: ...

    async def soft_delete(self, document_id: DocumentId) -> None: ...
