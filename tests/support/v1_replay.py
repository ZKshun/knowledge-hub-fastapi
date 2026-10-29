import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import httpx

from knowledge_hub.app.factory import create_app
from knowledge_hub.core.config import Settings
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from tests.support.v1_compare import compare_evidence
from tests.support.v1_state import seed_state, snapshot

FIXTURES = Path(__file__).parents[1] / "fixtures/contracts/v1"
CASES = {
    path.stem: json.loads(path.read_text(encoding="utf-8")) for path in FIXTURES.glob("[0-9]*.json")
}
DOCUMENTS = {
    name.split("_create_", 1)[1]: case["response"]["body"]["id"]
    for name, case in CASES.items()
    if "_create_" in name and case["response"]["status"] == 201
}


class ReplayIds:
    def __init__(self, identifier):
        self.identifier = DocumentId(identifier)

    def next_id(self):
        return self.identifier


async def replay_case(storage, name, case, previous):
    before = deepcopy(previous)
    if name.startswith("028_"):
        before["mongo"] = [
            row for row in before["mongo"] if row["documentId"] != DOCUMENTS["missing"]
        ]
    if name.startswith("075_"):
        for row in before["postgres"]:
            if row["id"] in {DOCUMENTS["full"], DOCUMENTS["archived"]}:
                row["created_at"] = "2099-01-01T00:00:00.000000"
    await seed_state(storage, before)
    expected = {"response": deepcopy(case["response"]), "state": deepcopy(case["state"])}
    _reliability_expectation(name, expected["state"], before)
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    app = create_app(Settings(_env_file=None), document_store=store)
    async with app.router.lifespan_context(app):
        app.state.document_services = replace(
            app.state.document_services, ids=ReplayIds(_identifier(case, before, name))
        )
        try:
            command = {"068": "insert", "070": "update", "073": "update", "074": "update"}.get(
                name[:3]
            )
            if command:
                await storage.mongo.client.admin.command(
                    {
                        "configureFailPoint": "failCommand",
                        "mode": {"times": 1},
                        "data": {"failCommands": [command], "errorCode": 2, "errorLabels": []},
                    }
                )
            request = case["request"]
            started = datetime.now(UTC)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client:
                response = await client.request(
                    request["method"], request["path"].format_map(DOCUMENTS), json=request["body"]
                )
            finished = datetime.now(UTC)
            actual = {
                "response": {
                    "status": response.status_code,
                    "contentType": response.headers.get("content-type"),
                    "body": response.json(),
                },
                "state": await snapshot(storage),
            }
            compare_evidence(
                expected,
                actual,
                before,
                started=started,
                finished=finished,
                ties=name.startswith("075_"),
            )
            if name.startswith("074_"):
                pending = await store.journal.list_pending()
                assert len(pending) == 1 and pending[0].state == "compensation_pending"
                assert pending[0].last_error == "OperationFailure"
                report = await store.recover_pending()
                assert report.compensated == 1 and report.failed == 0
                assert not any(
                    row["content"] == "orphan candidate"
                    for row in (await snapshot(storage))["mongo"]
                )
            else:
                assert await store.journal.list_pending() == []
        finally:
            await storage.mongo.client.admin.command(
                {"configureFailPoint": "failCommand", "mode": "off"}
            )


def _identifier(case, before, name):
    body = case["response"]["body"]
    if case["response"]["status"] == 201:
        return body["id"]
    existing = {row["documentId"] for row in before["mongo"]}
    added = [
        row["documentId"] for row in case["state"]["mongo"] if row["documentId"] not in existing
    ]
    return added[0] if added else str(8_000_000_000_000_000_000 + int(name[:3]))


def _reliability_expectation(name, expected, before):
    store, document = (
        ("mongo", "failure_update") if name.startswith("071_") else ("postgres", "failure_delete")
    )
    if name[:3] not in {"071", "073"}:
        return
    key = "documentId" if store == "mongo" else "id"
    original = next(row for row in before[store] if row[key] == DOCUMENTS[document])
    expected[store] = [
        deepcopy(original) if row[key] == original[key] else row for row in expected[store]
    ]
