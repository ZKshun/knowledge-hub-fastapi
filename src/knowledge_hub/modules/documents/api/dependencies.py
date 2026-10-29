from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request

from knowledge_hub.core.clock import Clock
from knowledge_hub.core.ids import IdGenerator
from knowledge_hub.modules.documents.api.requests import DocumentQueryRequest
from knowledge_hub.modules.documents.application.ports import DocumentStore


@dataclass(frozen=True, slots=True)
class DocumentServices:
    store: DocumentStore
    ids: IdGenerator
    clock: Clock


def get_services(request: Request) -> DocumentServices:
    return cast(DocumentServices, request.app.state.document_services)


def parse_query(request: Request) -> DocumentQueryRequest:
    data: dict[str, object] = {}
    for key in request.query_params:
        values = request.query_params.getlist(key)
        data[key] = values[0] if len(values) == 1 else values
    return DocumentQueryRequest.model_validate(data)


Services = Annotated[DocumentServices, Depends(get_services)]
QueryInput = Annotated[DocumentQueryRequest, Depends(parse_query)]
