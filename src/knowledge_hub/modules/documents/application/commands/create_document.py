from knowledge_hub.core.clock import Clock
from knowledge_hub.core.ids import IdGenerator
from knowledge_hub.modules.documents.application.ports import DocumentStore
from knowledge_hub.modules.documents.domain.commands import CreateDocumentCommand
from knowledge_hub.modules.documents.domain.document import Document, DocumentDetail, DocumentStatus
from knowledge_hub.modules.documents.domain.text_metrics import count_words


async def create_document(
    command: CreateDocumentCommand, *, store: DocumentStore, ids: IdGenerator, clock: Clock
) -> DocumentDetail:
    now = clock.now()
    status = command.status if command.status is not None else DocumentStatus.DRAFT
    document = Document(
        id=ids.next_id(),
        title=command.title,
        summary=command.summary,
        category_id=command.category_id,
        team_id=command.team_id,
        author_id=command.author_id,
        cover_image=command.cover_image,
        tags=command.tags,
        status=status,
        remark=command.remark,
        is_public=command.is_public if command.is_public is not None else False,
        word_count=count_words(command.content),
        publish_time=now.replace(microsecond=now.microsecond // 1000 * 1000)
        if status == DocumentStatus.PUBLISHED
        else None,
        create_by=command.create_by,
        update_by=command.create_by,
        created_at=now,
        updated_at=now,
    )
    return await store.create(DocumentDetail(document=document, content=command.content))
