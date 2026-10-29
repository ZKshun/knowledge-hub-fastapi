import httpx
from sqlalchemy import select

from knowledge_hub.app.factory import create_app
from knowledge_hub.core.config import Settings
from knowledge_hub.modules.documents.infrastructure.document_row import DocumentRow
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore
from tests.support.storage import Databases


async def test_real_http_contract_and_dual_database_lifecycle(storage: Databases) -> None:
    store = PostgresMongoDocumentStore(storage.postgres, storage.collection)
    app = create_app(Settings(_env_file=None), document_store=store)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/documents",
                json={
                    "title": "Lifecycle",
                    "content": "知识库 hello world",
                    "createBy": "9007199254740993",
                },
            )
            assert created.status_code == 201
            original = created.json()
            identifier = original["id"]
            assert original["createBy"] == original["updateBy"] == "9007199254740993"
            assert (await client.get(f"/documents/{identifier}")).json() == original
            page = (await client.get("/documents?title=life&pageSize=1")).json()
            assert page["total"] == 1 and "content" not in page["items"][0]
            for payload, version in [
                ({"content": "知识库 hello world"}, 2),
                ({"summary": "preview"}, 2),
                ({}, 2),
                ({"content": "", "status": 1}, 3),
            ]:
                response = await client.patch(f"/documents/{identifier}", json=payload)
                assert response.status_code == 200
                raw = await storage.collection.find_one({"documentId": identifier})
                assert raw is not None and raw["version"] == version
            assert response.json()["content"] == "" and response.json()["wordCount"] == 0
            assert response.json()["publishTime"].endswith("Z")
            assert (await client.delete(f"/documents/{identifier}")).json() == {
                "id": identifier,
                "deleted": True,
            }
            assert (await client.get(f"/documents/{identifier}")).status_code == 404
            assert (await client.delete(f"/documents/{identifier}")).status_code == 404
            assert (await client.get("/documents")).json()["total"] == 0
    raw = await storage.collection.find_one({"documentId": identifier})
    assert raw is not None and raw["content"] == "" and raw["version"] == 3 and raw["deleted"]
    assert str(raw["_id"]) == original["contentId"]
    async with storage.postgres.sessions() as session:
        row = await session.scalar(select(DocumentRow).where(DocumentRow.id == int(identifier)))
        assert row is not None and row.deleted and row.word_count == 0
