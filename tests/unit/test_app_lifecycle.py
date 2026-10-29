import importlib
import json
import logging

import httpx
import pytest
from pydantic import ValidationError

from knowledge_hub.app import lifespan
from knowledge_hub.app.factory import create_app
from knowledge_hub.core.config import Settings
from tests.contract.api_support import MemoryStore


def test_main_import_does_not_read_environment_or_construct_clients(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Import attempted configuration or I/O")

    monkeypatch.setattr(lifespan, "Settings", forbidden)
    monkeypatch.setattr(lifespan, "PostgresDatabase", forbidden)
    monkeypatch.setattr(lifespan, "MongoDatabase", forbidden)
    module = importlib.import_module("knowledge_hub.main")
    assert module.app is not None


def test_cli_uses_port_from_explicit_process_environment(monkeypatch):
    module = importlib.import_module("knowledge_hub.main")
    observed = []
    monkeypatch.setenv("PORT", "8123")
    monkeypatch.setattr(
        module.uvicorn, "run", lambda *args, **kwargs: observed.append((args, kwargs))
    )
    module.run([])
    assert observed[0][1]["port"] == 8123


def test_cli_explicit_env_file_controls_server_port(tmp_path, monkeypatch):
    module = importlib.import_module("knowledge_hub.main")
    env_file = tmp_path / "explicit.env"
    env_file.write_text("PORT=8124\n", encoding="utf-8")
    monkeypatch.delenv("PORT", raising=False)
    observed = []
    monkeypatch.setattr(
        module.uvicorn, "run", lambda *args, **kwargs: observed.append((args, kwargs))
    )
    module.run(["--env-file", str(env_file)])
    assert observed[0][1]["port"] == 8124


async def test_default_settings_errors_are_deferred_to_startup(monkeypatch):
    monkeypatch.setenv("PORT", "invalid")
    app = create_app()
    with pytest.raises(ValidationError):
        async with app.router.lifespan_context(app):
            pytest.fail("Invalid configuration must reject startup")


async def test_injected_store_does_not_construct_real_clients(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Injected store attempted to create a client")

    monkeypatch.setattr(lifespan, "PostgresDatabase", forbidden)
    monkeypatch.setattr(lifespan, "MongoDatabase", forbidden)
    app = create_app(Settings(_env_file=None), document_store=MemoryStore())
    with pytest.raises(RuntimeError, match="application interrupted"):
        async with app.router.lifespan_context(app):
            assert app.state.document_services.store is not None
            raise RuntimeError("application interrupted")
    assert not hasattr(app.state, "document_services")


async def test_request_logging_correlates_errors_without_private_body(caplog):
    class FailingStore(MemoryStore):
        async def get(self, document_id):
            raise RuntimeError("PRIVATE_BODY_SENTINEL")

    app = create_app(Settings(_env_file=None), document_store=FailingStore())
    caplog.set_level(logging.INFO, logger="knowledge_hub")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/documents/101", headers={"x-request-id": "contract-request-1"}
            )
    assert response.status_code == 500
    assert response.headers["x-request-id"] == "contract-request-1"
    events = [
        json.loads(record.message)
        for record in caplog.records
        if record.name.startswith("knowledge_hub")
    ]
    assert any(
        e.get("request_id") == "contract-request-1" and e.get("error_type") == "RuntimeError"
        for e in events
    )
    assert "PRIVATE_BODY_SENTINEL" not in caplog.text + response.text
