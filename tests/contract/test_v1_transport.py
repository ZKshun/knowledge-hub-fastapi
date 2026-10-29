import hashlib
import json
from pathlib import Path

import httpx
import pytest

from knowledge_hub.app.factory import create_app
from knowledge_hub.core.config import Settings
from tests.contract.api_support import MemoryStore

FIXTURES = Path(__file__).parents[1] / "fixtures/contracts"
SUPPLEMENT = json.loads((FIXTURES / "v1-http-boundaries.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "case",
    SUPPLEMENT["cases"],
    ids=lambda c: c.get("reviewSupplement") or c["method"] + c["path"] + str(c.get("rawBody"))[:80],
)
async def test_real_legacy_transport_behavior_is_preserved(case):
    store = MemoryStore()
    app = create_app(Settings(_env_file=None), document_store=store)
    body = case["rawBody"]
    if "rawBodyHex" in case:
        body = bytes.fromhex(case["rawBodyHex"])
    if "rawBodySpec" in case:
        spec = case["rawBodySpec"]
        body = json.dumps({"title": "x" * spec["titleLength"], "content": spec["content"]})
    if body is not None:
        encoded = body if isinstance(body, bytes) else body.encode()
        assert hashlib.sha256(encoded).hexdigest() == case["rawBodySha256"]
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            headers = {}
            if case.get("requestContentType") is not None:
                headers["content-type"] = case["requestContentType"]
            if case.get("requestContentEncoding") is not None:
                headers["content-encoding"] = case["requestContentEncoding"]
            response = await client.request(
                case["method"],
                case["path"],
                content=body,
                headers=headers,
            )
    assert response.status_code == case["status"]
    assert response.headers["content-type"] == case["contentType"]
    assert response.headers.get("allow") == case["allow"]
    if case["body"] is not None:
        assert response.json() == json.loads(case["body"])
    if case["method"] == "HEAD":
        assert response.content == b""
    if case.get("reviewSupplement") == "review-final-rootless-form":
        assert store.documents == {}


def test_supplement_uses_same_compiled_fixed_source_as_original_baseline():
    manifest = json.loads((FIXTURES / "v1/manifest.json").read_text(encoding="utf-8"))
    assert SUPPLEMENT["sourceCommit"] == manifest["sourceCommit"]
    assert SUPPLEMENT["compiledMainSha256"] == manifest["compiledMainSha256"]
