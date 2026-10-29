import json
import logging
import re
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
_LOGGER = logging.getLogger("knowledge_hub.http")


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("knowledge_hub").setLevel(logging.INFO)


def log_failure(error_type: str, request_id: str | None) -> None:
    _LOGGER.error(
        json.dumps({"event": "request_failed", "request_id": request_id, "error_type": error_type})
    )


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        supplied = Headers(scope=scope).get("x-request-id", "")
        request_id = supplied if _REQUEST_ID.fullmatch(supplied) else str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_context.set(request_id)
        status, started = 500, perf_counter()

        async def correlated_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message).setdefault("x-request-id", request_id)
            await send(message)

        try:
            await self.app(scope, receive, correlated_send)
        finally:
            _LOGGER.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": scope["method"],
                        "status": status,
                        "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                    }
                )
            )
            request_id_context.reset(token)
