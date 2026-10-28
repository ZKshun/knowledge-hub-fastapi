import json
from pathlib import Path

import httpx
import pytest

from scripts.legacy_v1.capture import CaptureSession
from scripts.legacy_v1.guards import validate_database_targets, validate_http_target


@pytest.mark.parametrize("url", ["https://example.com", "http://127.0.0.1:3000"])
def test_capture_rejects_nonisolated_http_targets(url: str) -> None:
    with pytest.raises(ValueError, match="3101"):
        validate_http_target(url)


def test_capture_accepts_only_dedicated_database_names_and_ports() -> None:
    validate_http_target("http://127.0.0.1:3101")
    validate_database_targets(
        "postgresql://kh_test:local-contract-only@127.0.0.1:55432/knowledge_hub_fastapi_test",
        "mongodb://127.0.0.1:57017/knowledge_hub_fastapi_test",
    )
    with pytest.raises(ValueError, match="isolated"):
        validate_database_targets(
            "postgresql://user:password@127.0.0.1:55432/knowledge_hub",
            "mongodb://127.0.0.1:57017/knowledge_hub_fastapi_test",
        )


def test_capture_rejects_connection_query_overrides() -> None:
    with pytest.raises(ValueError, match="isolated"):
        validate_database_targets(
            "postgresql://test:test@127.0.0.1:55432/knowledge_hub_fastapi_test?host=remote",
            "mongodb://127.0.0.1:57017/knowledge_hub_fastapi_test",
        )


class StaticProbe:
    def snapshot(self) -> dict[str, object]:
        return {"postgres": [{"id": "9007199254740993"}], "mongo": []}


def test_capture_records_real_http_status_body_request_and_side_effects(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            201,
            json={"id": "9007199254740993", "content": "synthetic", "summary": None},
        )
    )
    with httpx.Client(base_url="http://127.0.0.1:3101", transport=transport) as http:
        capture = CaptureSession(http, StaticProbe(), tmp_path)
        capture.record("create_minimal", "POST", "/documents", body={"content": "synthetic"})
    record = json.loads((tmp_path / "001_create_minimal.json").read_text(encoding="utf-8"))
    assert record["request"] == {
        "method": "POST",
        "path": "/documents",
        "body": {"content": "synthetic"},
    }
    assert record["response"]["status"] == 201
    assert record["response"]["body"]["summary"] is None
    assert record["state"]["postgres"][0]["id"] == "9007199254740993"
    assert record["normalized"]["response"]["body"]["id"] == "@document:1"
    assert record["normalized"]["state"]["postgres"][0]["id"] == "@document:1"


def test_capture_refuses_to_overwrite_existing_evidence(tmp_path: Path) -> None:
    (tmp_path / "001_create_minimal.json").write_text("existing evidence", encoding="utf-8")
    with httpx.Client(
        base_url="http://127.0.0.1:3101",
        transport=httpx.MockTransport(lambda request: httpx.Response(201, json={"id": "1"})),
    ) as http:
        capture = CaptureSession(http, StaticProbe(), tmp_path)
        with pytest.raises(FileExistsError):
            capture.record("create_minimal", "POST", "/documents", body={})
    assert (tmp_path / "001_create_minimal.json").read_text() == "existing evidence"


def test_capture_normalizes_generated_id_inside_known_not_found_error(tmp_path: Path) -> None:
    content_id = "0123456789abcdef01234567"

    def respond(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(201, json={"id": "123", "contentId": content_id})
        return httpx.Response(400, json={"message": f"Document content {content_id} not found"})

    with httpx.Client(
        base_url="http://127.0.0.1:3101", transport=httpx.MockTransport(respond)
    ) as http:
        capture = CaptureSession(http, StaticProbe(), tmp_path)
        capture.record("create", "POST", "/documents", body={})
        capture.record("missing", "PATCH", "/documents/123", body={})
    record = json.loads((tmp_path / "002_missing.json").read_text(encoding="utf-8"))
    assert record["response"]["body"]["message"] == f"Document content {content_id} not found"
    assert record["normalized"]["response"]["body"]["message"] == (
        "Document content @content:1 not found"
    )


def test_capture_keeps_timestamp_wire_formats_distinct(tmp_path: Path) -> None:
    normalized = []
    for label, timestamp in [
        ("z", "2026-10-28T00:00:00.000Z"),
        ("offset", "2026-10-28T00:00:00.000+00:00"),
    ]:
        output = tmp_path / label
        with httpx.Client(
            base_url="http://127.0.0.1:3101",
            transport=httpx.MockTransport(
                lambda request, value=timestamp: httpx.Response(201, json={"createdAt": value})
            ),
        ) as http:
            CaptureSession(http, StaticProbe(), output).record("create", "POST", "/documents")
        record = json.loads((output / "001_create.json").read_text(encoding="utf-8"))
        normalized.append(record["normalized"]["response"]["body"]["createdAt"])
    assert normalized[0] != normalized[1]
