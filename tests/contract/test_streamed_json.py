from uuid import UUID

import httpx
import pytest

from knowledge_hub.app.factory import create_app
from knowledge_hub.app.transport import LegacyTransportMiddleware
from knowledge_hub.core.config import Settings
from knowledge_hub.core.logging import request_id_context
from tests.contract.api_support import MemoryStore


async def test_chunked_json_is_replayed_once_without_losing_fields():
    async def chunks():
        for part in [b'{"title":', b'"T","content":', b'"body"}']:
            yield part

    app = create_app(Settings(_env_file=None), document_store=MemoryStore())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/documents",
                content=chunks(),
                headers={"content-type": "application/json", "x-request-id": "bad value"},
            )
    assert response.status_code == 201
    assert response.json()["title"] == "T" and response.json()["content"] == "body"
    assert str(UUID(response.headers["x-request-id"])) == response.headers["x-request-id"]
    assert request_id_context.get() is None


async def test_streaming_over_limit_stops_consuming_before_unbounded_body():
    sent = 0

    async def chunks():
        nonlocal sent
        for _ in range(1000):
            sent += 1
            yield b" " * 8192

    app = create_app(Settings(_env_file=None), document_store=MemoryStore())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/documents", content=chunks(), headers={"content-type": "application/json"}
            )
    assert response.status_code == 413 and sent < 1000
    assert response.json() == {"statusCode": 413, "message": "request entity too large"}


async def test_disconnect_during_json_upload_never_dispatches_business_handler():
    async def forbidden(scope, receive, send):
        pytest.fail("Disconnected request reached business code")

    async def receive():
        return {"type": "http.disconnect"}

    sent = []

    async def send(message):
        sent.append(message)

    await LegacyTransportMiddleware(forbidden)(
        {
            "type": "http",
            "path": "/documents",
            "method": "POST",
            "headers": [(b"content-type", b"application/json"), (b"transfer-encoding", b"chunked")],
        },
        receive,
        send,
    )
    assert sent == []
