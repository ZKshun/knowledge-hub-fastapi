from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from knowledge_hub.app.responses import LegacyJSONResponse
from knowledge_hub.core.errors import ApplicationError, DocumentContentNotFound, DocumentNotFound
from knowledge_hub.core.logging import log_failure
from knowledge_hub.modules.documents.api.validation import LegacyValidationError


async def application_error(request: Request, error: Exception) -> LegacyJSONResponse:
    if isinstance(error, LegacyValidationError):
        return LegacyJSONResponse(
            {"message": error.messages, "error": "Bad Request", "statusCode": 400}, status_code=400
        )
    if isinstance(error, (DocumentNotFound, DocumentContentNotFound)):
        code = 404 if isinstance(error, DocumentNotFound) else 400
        return LegacyJSONResponse(
            {
                "message": str(error),
                "error": "Not Found" if code == 404 else "Bad Request",
                "statusCode": code,
            },
            status_code=code,
        )
    request_id = getattr(request.state, "request_id", None)
    log_failure(type(error).__name__, request_id)
    headers = {"x-request-id": request_id} if isinstance(request_id, str) else None
    return LegacyJSONResponse(
        {"statusCode": 500, "message": "Internal server error"}, status_code=500, headers=headers
    )


async def request_error(request: Request, error: Exception) -> LegacyJSONResponse:
    return LegacyJSONResponse(
        {"message": ["Invalid request body"], "error": "Bad Request", "statusCode": 400},
        status_code=400,
    )


async def http_error(request: Request, error: Exception) -> LegacyJSONResponse:
    assert isinstance(error, HTTPException)
    code = 404 if error.status_code == 405 else error.status_code
    path = request.scope.get("legacy_original_path", request.url.path)
    message = f"Cannot {request.method} {path}" if code == 404 else str(error.detail)
    return LegacyJSONResponse(
        {
            "message": message,
            "error": "Not Found" if code == 404 else "Bad Request",
            "statusCode": code,
        },
        status_code=code,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error)
    app.add_exception_handler(LegacyValidationError, application_error)
    app.add_exception_handler(RequestValidationError, request_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(Exception, application_error)
