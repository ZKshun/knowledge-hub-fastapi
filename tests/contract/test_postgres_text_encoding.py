import json
from pathlib import Path

import httpx
from sqlalchemy import select

from knowledge_hub.app.factory import create_app
from knowledge_hub.core.config import Settings
from knowledge_hub.modules.documents.infrastructure.document_row import DocumentRow
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore

SOURCE = json.loads(
    (Path(__file__).parents[1] / "fixtures/contracts/v1-text-encoding.json").read_text(
        encoding="utf-8"
    )
)
FIELDS = {
    "title": "title",
    "summary": "summary",
    "coverImage": "cover_image",
    "tags": "tags",
    "remark": "remark",
}


async def test_postgres_node_utf8_encoding_preserves_create_response_and_readback(storage):
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    app = create_app(Settings(_env_file=None), document_store=store)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/documents",
                content=json.dumps(SOURCE["request"]),
                headers={"content-type": "application/json"},
            )
            assert created.status_code == 201
            identifier = created.json()["id"]
            detail = (await client.get("/documents/" + identifier)).json()
            for wire in FIELDS:
                assert created.json()[wire] == SOURCE["created"][wire]
                assert detail[wire] == SOURCE["detail"][wire]
            async with storage.postgres.sessions() as session:
                row = await session.scalar(
                    select(DocumentRow).where(DocumentRow.id == int(identifier))
                )
                assert row is not None
                for column in FIELDS.values():
                    assert getattr(row, column) == SOURCE["state"]["postgres"][0][column]
            patched = await client.patch(
                "/documents/" + identifier,
                content=json.dumps({"title": "Updated \ud83e"}),
                headers={"content-type": "application/json"},
            )
            assert patched.status_code == 200 and patched.json()["title"] == "Updated \ud83e"
            assert (await client.get("/documents/" + identifier)).json()[
                "title"
            ] == "Updated \ufffd"
