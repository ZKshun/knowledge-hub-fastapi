from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from knowledge_hub.app.error_handlers import application_error
from knowledge_hub.core.logging import log_failure


class SafeExceptionMiddleware:
    """Consume HTTP failures before Uvicorn can log private exception messages."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def observed_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        except Exception as error:
            request = Request(scope, receive=receive)
            if started:
                log_failure(type(error).__name__, getattr(request.state, "request_id", None))
                return
            response = await application_error(request, error)
            try:
                await response(scope, receive, send)
            except Exception as delivery_error:
                log_failure(
                    type(delivery_error).__name__, getattr(request.state, "request_id", None)
                )
