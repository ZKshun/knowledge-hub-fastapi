from fastapi import FastAPI

from knowledge_hub.app.error_handlers import register_error_handlers
from knowledge_hub.app.lifespan import application_lifespan
from knowledge_hub.app.openapi import configure_openapi
from knowledge_hub.app.responses import LegacyJSONResponse
from knowledge_hub.app.routes import register_routes
from knowledge_hub.app.safe_errors import SafeExceptionMiddleware
from knowledge_hub.app.transport import LegacyTransportMiddleware
from knowledge_hub.core.config import Settings
from knowledge_hub.core.logging import RequestLoggingMiddleware
from knowledge_hub.modules.documents.application.ports import DocumentStore


def create_app(
    settings: Settings | None = None,
    *,
    document_store: DocumentStore | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Knowledge Hub",
        version="0.1.0",
        default_response_class=LegacyJSONResponse,
        redirect_slashes=False,
        lifespan=lambda app: application_lifespan(app, settings, document_store),
    )
    register_error_handlers(app)
    register_routes(app)
    configure_openapi(app)
    app.add_middleware(LegacyTransportMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SafeExceptionMiddleware)
    return app
