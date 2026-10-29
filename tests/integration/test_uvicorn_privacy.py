import asyncio
import logging
import socket

import httpx
import uvicorn

from knowledge_hub.app.factory import create_app
from knowledge_hub.core.config import Settings
from tests.contract.api_support import MemoryStore


async def test_real_uvicorn_does_not_log_private_exception_or_rethrow(caplog):
    class FailingStore(MemoryStore):
        async def get(self, document_id):
            raise RuntimeError("PRIVATE_UVICORN_SENTINEL")

    caplog.set_level(logging.INFO)
    app = create_app(Settings(_env_file=None), document_store=FailingStore())
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    listener.setblocking(False)
    ready = asyncio.Event()

    class ReadyServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            ready.set()

    server = ReadyServer(
        uvicorn.Config(
            app, log_config=None, access_log=False, lifespan="on", timeout_graceful_shutdown=2
        )
    )
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        await asyncio.wait_for(ready.wait(), 3)
        assert server.started
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{listener.getsockname()[1]}", trust_env=False
        ) as client:
            response = await client.get(
                "/documents/101", headers={"x-request-id": "uvicorn-privacy"}
            )
            assert response.status_code == 500
            assert response.json() == {"statusCode": 500, "message": "Internal server error"}
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 3)
        listener.close()
    assert "PRIVATE_UVICORN_SENTINEL" not in caplog.text
    assert '"error_type": "RuntimeError"' in caplog.text
    assert "Exception in ASGI application" not in caplog.text
