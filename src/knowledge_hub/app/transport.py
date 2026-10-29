from starlette.types import ASGIApp, Message, Receive, Scope, Send

from knowledge_hub.app.body_reader import prepare_request_body
from knowledge_hub.app.responses import LegacyJSONResponse
from knowledge_hub.integrations.http.errors import BodyDecodingError


class LegacyTransportMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        if path.split("/")[1:2] and path.split("/")[1].lower() == "documents":
            scope["legacy_original_path"] = path
            normalized = "/documents" + path[len("/documents") :]
            scope["path"] = normalized[:-1] if normalized.endswith("/") else normalized
        try:
            prepared, body = await prepare_request_body(scope, receive)
        except BodyDecodingError as error:
            payload: dict[str, object] = {"statusCode": error.status_code, "message": error.message}
            if error.error_label is not None:
                payload["error"] = error.error_label
            await LegacyJSONResponse(payload, status_code=error.status_code)(scope, receive, send)
            return
        if prepared:
            if body is None:
                return
            original_receive, consumed = receive, False

            async def replay_body() -> Message:
                nonlocal consumed
                if consumed:
                    return await original_receive()
                consumed = True
                return {"type": "http.request", "body": body, "more_body": False}

            receive = replay_body
        await self.app(scope, receive, send)
