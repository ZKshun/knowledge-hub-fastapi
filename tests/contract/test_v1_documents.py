import json
from pathlib import Path

import httpx
import pytest

from knowledge_hub.app.factory import create_app
from knowledge_hub.core.config import Settings
from tests.contract.api_support import MemoryStore

FIXTURES = Path(__file__).parents[1] / "fixtures/contracts/v1"
VALIDATION = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted(FIXTURES.glob("[0-9]*.json"))
    if json.loads(path.read_text(encoding="utf-8"))["response"]["status"] == 400
    and not path.name.startswith("029")
]


@pytest.fixture
async def client():
    app = create_app(Settings(_env_file=None), document_store=MemoryStore())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as http:
            yield http


@pytest.mark.parametrize(
    "case", VALIDATION, ids=lambda c: c["request"]["path"] + str(c["request"]["body"])
)
async def test_validation_matches_original_messages_order_types_and_content_type(
    client, case
) -> None:
    request = case["request"]
    response = await client.request(
        request["method"], request["path"].replace("{full}", "101"), json=request["body"]
    )
    assert response.status_code == case["response"]["status"]
    assert response.headers["content-type"] == case["response"]["contentType"]
    assert response.json() == case["response"]["body"]


async def test_five_routes_preserve_wire_fields_defaults_and_string_ids(client) -> None:
    created = await client.post("/documents", json={"title": "T", "content": "知识库 hello world"})
    assert created.status_code == 201
    body = created.json()
    expected_fields = set(
        json.loads((FIXTURES / "001_create_minimal.json").read_text(encoding="utf-8"))["response"][
            "body"
        ]
    )
    assert body.keys() == expected_fields
    assert isinstance(body["id"], str) and body["summary"] is None
    assert body["wordCount"] == 5 and body["status"] == 0 and body["isPublic"] is False
    assert body["createdAt"].endswith("Z") and len(body["createdAt"].split(".")[1]) == 4
    identifier = body["id"]
    assert (await client.get(f"/documents/{identifier}")).json() == body
    page = (await client.get("/documents")).json()
    assert page.keys() == {"items", "total", "page", "pageSize"}
    assert "content" not in page["items"][0]
    changed = await client.patch(
        f"/documents/{identifier}", json={"title": "Renamed", "summary": None}
    )
    assert changed.status_code == 200 and changed.json()["title"] == "Renamed"
    assert changed.json()["content"] == body["content"]
    assert (await client.delete(f"/documents/{identifier}")).json() == {
        "id": identifier,
        "deleted": True,
    }
    missing = await client.get(f"/documents/{identifier}")
    assert missing.status_code == 404
    assert missing.json() == {
        "message": f"Document {identifier} not found",
        "error": "Not Found",
        "statusCode": 404,
    }


@pytest.mark.parametrize("field", ["title", "content", "status", "isPublic"])
async def test_patch_null_required_column_keeps_legacy_500(client, field: str) -> None:
    identifier = (await client.post("/documents", json={"title": "T", "content": "body"})).json()[
        "id"
    ]
    response = await client.patch(f"/documents/{identifier}", json={field: None})
    assert response.status_code == 500
    assert response.json() == {"statusCode": 500, "message": "Internal server error"}


@pytest.mark.parametrize(
    "query,page,size,status",
    [
        ("page=0x10&pageSize=0b10&status=", 16, 2, 0),
        ("page=1e1&pageSize=1.0&status=999", 10, 1, 999),
        ("page=%EF%BB%BF2%20&pageSize=0o10", 2, 8, None),
    ],
)
async def test_query_number_conversion_preserves_javascript_rules(
    client, query, page, size, status
):
    response = await client.get(f"/documents?{query}")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": page, "pageSize": size}


async def test_multiple_query_errors_keep_legacy_constraint_order(client):
    response = await client.get("/documents?page=n&pageSize=n&status=n")
    assert response.status_code == 400
    assert response.json()["message"] == [
        "status must be an integer number",
        "page must not be less than 1",
        "page must be an integer number",
        "pageSize must not be greater than 100",
        "pageSize must not be less than 1",
        "pageSize must be an integer number",
    ]


async def test_unicode_body_can_return_unpaired_surrogate_as_valid_json(client):
    response = await client.post(
        "/documents",
        content=json.dumps({"title": "T", "content": "a\ud83e"}),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 201 and response.json()["content"] == "a\ud83e"


async def test_multi_field_patch_errors_put_own_update_by_before_inherited_fields(client):
    response = await client.patch(
        "/documents/101",
        json={"updateBy": 2, "title": 2, "content": 2, "status": 3, "isPublic": 4, "unexpected": 1},
    )
    assert response.status_code == 400
    assert response.json()["message"] == [
        "property unexpected should not exist",
        "updateBy must be a string",
        "title must be a string",
        "content must be a string",
        "status must be one of the following values: 0, 1, 2",
        "isPublic must be a boolean value",
    ]


async def test_repeated_query_values_remain_arrays_and_fail_original_constraints(client):
    response = await client.get("/documents?page=1&page=2&title=a&title=b")
    assert response.status_code == 400
    assert response.json()["message"] == [
        "title must be a string",
        "page must not be less than 1",
        "page must be an integer number",
    ]


@pytest.mark.parametrize("status,code", [(1.0, 201), (True, 400), ("Published", 500)])
async def test_numeric_enum_and_boolean_follow_javascript_validation(client, status, code):
    response = await client.post(
        "/documents", json={"title": "T", "content": "B", "status": status}
    )
    assert response.status_code == code


async def test_openapi_exposes_query_contract_and_actual_validation_status(client):
    schema = (await client.get("/openapi.json")).json()
    operation = schema["paths"]["/documents"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert set(parameters) == {
        "title",
        "categoryId",
        "teamId",
        "authorId",
        "status",
        "page",
        "pageSize",
    }
    assert parameters["page"]["schema"]["minimum"] == 1
    assert parameters["pageSize"]["schema"]["maximum"] == 100
    for path in ("/documents", "/documents/{document_id}"):
        for operation in schema["paths"][path].values():
            assert "400" in operation["responses"]
            assert "422" not in operation["responses"]
