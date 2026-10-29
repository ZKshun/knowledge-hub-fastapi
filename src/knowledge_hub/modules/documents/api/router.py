from typing import Annotated

from fastapi import APIRouter, Body

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.api.dependencies import QueryInput, Services
from knowledge_hub.modules.documents.api.mappers import (
    create_command,
    document_query,
    document_response,
    page_response,
    update_command,
)
from knowledge_hub.modules.documents.api.query_schema import query_parameters
from knowledge_hub.modules.documents.api.requests import (
    CreateDocumentRequest,
    UpdateDocumentRequest,
)
from knowledge_hub.modules.documents.api.responses import (
    DeleteDocumentResponse,
    DocumentPageResponse,
    DocumentResponse,
    ErrorResponse,
)
from knowledge_hub.modules.documents.application.commands.create_document import create_document
from knowledge_hub.modules.documents.application.commands.delete_document import delete_document
from knowledge_hub.modules.documents.application.commands.update_document import update_document
from knowledge_hub.modules.documents.application.queries.get_document import get_document
from knowledge_hub.modules.documents.application.queries.list_documents import list_documents

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)


@router.post("", status_code=201)
async def create(
    services: Services,
    payload: Annotated[CreateDocumentRequest | None, Body()] = None,
) -> DocumentResponse:
    request = payload if payload is not None else CreateDocumentRequest.model_validate({})
    detail = await create_document(
        create_command(request),
        store=services.store,
        ids=services.ids,
        clock=services.clock,
    )
    return document_response(detail)


@router.get("", openapi_extra={"parameters": query_parameters()})
@router.head("", include_in_schema=False)
async def page(query: QueryInput, services: Services) -> DocumentPageResponse:
    return page_response(await list_documents(document_query(query), store=services.store))


@router.get("/{document_id}")
@router.head("/{document_id}", include_in_schema=False)
async def get(document_id: str, services: Services) -> DocumentResponse:
    return document_response(await get_document(DocumentId(document_id), store=services.store))


@router.patch("/{document_id}")
async def patch(
    document_id: str,
    services: Services,
    payload: Annotated[UpdateDocumentRequest | None, Body()] = None,
) -> DocumentResponse:
    request = payload if payload is not None else UpdateDocumentRequest.model_validate({})
    detail = await update_document(
        DocumentId(document_id),
        update_command(request),
        store=services.store,
        clock=services.clock,
    )
    return document_response(detail)


@router.delete("/{document_id}")
async def delete(document_id: str, services: Services) -> DeleteDocumentResponse:
    result = await delete_document(DocumentId(document_id), store=services.store)
    return DeleteDocumentResponse(id=result.document_id, deleted=result.deleted)
