from dataclasses import asdict
from typing import cast

from knowledge_hub.core.errors import InvalidDocumentChange
from knowledge_hub.modules.documents.api.requests import (
    CreateDocumentRequest,
    DocumentQueryRequest,
    UpdateDocumentRequest,
)
from knowledge_hub.modules.documents.api.responses import (
    DocumentMetadataResponse,
    DocumentPageResponse,
    DocumentResponse,
)
from knowledge_hub.modules.documents.domain.commands import (
    CreateDocumentCommand,
    DocumentFieldValue,
    DocumentQuery,
    UpdateDocumentCommand,
)
from knowledge_hub.modules.documents.domain.document import (
    DocumentDetail,
    DocumentPage,
    DocumentStatus,
)


def create_command(request: CreateDocumentRequest) -> CreateDocumentCommand:
    status = request.status
    if isinstance(status, str):
        # Numeric TypeScript enums also validate their labels; legacy SQL then fails.
        raise InvalidDocumentChange("Document status label cannot be persisted")
    return CreateDocumentCommand(
        title=request.title,
        content=request.content,
        summary=request.summary,
        category_id=request.category_id,
        team_id=request.team_id,
        author_id=request.author_id,
        cover_image=request.cover_image,
        tags=request.tags,
        remark=request.remark,
        status=DocumentStatus(status) if status is not None else None,
        is_public=request.is_public,
        create_by=request.create_by,
    )


def update_command(request: UpdateDocumentRequest) -> UpdateDocumentCommand:
    return UpdateDocumentCommand(
        changes=cast(
            dict[str, DocumentFieldValue],
            request.model_dump(exclude_unset=True),
        )
    )


def document_query(request: DocumentQueryRequest) -> DocumentQuery:
    return DocumentQuery(
        title=request.title,
        category_id=request.category_id,
        team_id=request.team_id,
        author_id=request.author_id,
        status=request.status,
        page=request.page,
        page_size=request.page_size,
    )


def document_response(detail: DocumentDetail) -> DocumentResponse:
    return DocumentResponse.model_validate({**asdict(detail.document), "content": detail.content})


def page_response(page: DocumentPage) -> DocumentPageResponse:
    return DocumentPageResponse(
        items=[
            DocumentMetadataResponse.model_validate(asdict(document)) for document in page.items
        ],
        total=page.total,
        page=page.page,
        page_size=page.page_size,
    )
