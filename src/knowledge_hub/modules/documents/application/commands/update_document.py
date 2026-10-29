from dataclasses import replace

from knowledge_hub.core.clock import Clock
from knowledge_hub.core.errors import InvalidDocumentChange
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.application.ports import DocumentStore
from knowledge_hub.modules.documents.domain.commands import (
    DocumentFieldValue,
    DocumentMutation,
    UpdateDocumentCommand,
)
from knowledge_hub.modules.documents.domain.document import Document, DocumentDetail, DocumentStatus
from knowledge_hub.modules.documents.domain.text_metrics import count_words


async def update_document(
    document_id: DocumentId,
    command: UpdateDocumentCommand,
    *,
    store: DocumentStore,
    clock: Clock,
) -> DocumentDetail:
    def transform(current: DocumentDetail) -> DocumentMutation:
        changes = command.changes
        for field in ("title", "content", "status", "is_public"):
            if field in changes and changes[field] is None:
                # Legacy optional DTO accepts null; its service/storage then fails (HTTP 500).
                raise InvalidDocumentChange(f"Document {field} cannot be null")
        content = changes.get("content", current.content)
        if not isinstance(content, str):
            raise InvalidDocumentChange("Document content must be a string")
        document = _metadata(current.document, command)
        if "content" in changes:
            document = replace(document, word_count=count_words(content))
        if (
            document.status == DocumentStatus.PUBLISHED
            and current.document.status != document.status
        ):
            now = clock.now()
            document = replace(
                document, publish_time=now.replace(microsecond=now.microsecond // 1000 * 1000)
            )
        if document != current.document:
            document = replace(document, updated_at=clock.now())
        return DocumentMutation(
            target=DocumentDetail(document=document, content=content),
            provided_fields=frozenset(command.changes),
        )

    return await store.mutate(document_id, transform)


def _text(value: DocumentFieldValue) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise InvalidDocumentChange("Document text fields must contain strings or null")


def _metadata(document: Document, command: UpdateDocumentCommand) -> Document:
    changes = command.changes
    title = changes.get("title", document.title)
    status = changes.get("status", document.status)
    is_public = changes.get("is_public", document.is_public)
    if not isinstance(title, str) or not isinstance(status, int) or not isinstance(is_public, bool):
        raise InvalidDocumentChange("Invalid required document metadata")
    return replace(
        document,
        title=title,
        status=DocumentStatus(status),
        is_public=is_public,
        summary=_text(changes.get("summary", document.summary)),
        category_id=_text(changes.get("category_id", document.category_id)),
        team_id=_text(changes.get("team_id", document.team_id)),
        author_id=_text(changes.get("author_id", document.author_id)),
        cover_image=_text(changes.get("cover_image", document.cover_image)),
        tags=_text(changes.get("tags", document.tags)),
        remark=_text(changes.get("remark", document.remark)),
        update_by=_text(changes.get("update_by", document.update_by)),
    )
