from datetime import UTC, datetime

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.domain.document import Document, DocumentDetail


class ProcessStopped(BaseException):
    pass


def draft(document_id: str = "101") -> DocumentDetail:
    return DocumentDetail(
        document=Document(
            id=DocumentId(document_id),
            title="Synthetic",
            word_count=5,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        content="知识库 hello world",
    )
