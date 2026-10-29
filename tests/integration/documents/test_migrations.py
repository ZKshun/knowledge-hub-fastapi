import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.documents.conftest import Databases


async def test_upgrade_downgrade_upgrade_preserves_legacy_schema(databases: Databases) -> None:
    await databases.migrate()
    async with databases.postgres.engine.connect() as connection:
        columns = await connection.run_sync(
            lambda sync: inspect(sync).get_columns("kh_document", schema=databases.schema)
        )
        actual = {c["name"]: (str(c["type"]), c["nullable"]) for c in columns}
        legacy = await connection.run_sync(
            lambda sync: inspect(sync).get_columns("kh_document", schema="public")
        )
        assert actual == {c["name"]: (str(c["type"]), c["nullable"]) for c in legacy}
        assert actual["id"] == ("BIGINT", False)
        assert actual["title"] == ("VARCHAR", False)
        assert actual["created_at"] == ("TIMESTAMP", False)
        defaults = {c["name"]: c["default"] for c in columns}
        assert defaults == {c["name"]: c["default"] for c in legacy}
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
    await databases.migrate("base")
    async with databases.postgres.engine.connect() as connection:
        assert (
            await connection.run_sync(lambda sync: inspect(sync).has_table("kh_document")) is False
        )
        assert (
            await connection.run_sync(lambda sync: inspect(sync).has_table("kh_document_operation"))
            is False
        )
    await databases.migrate()
    await databases.migrate()


async def test_existing_unversioned_table_is_rejected_without_overwrite(
    databases: Databases,
) -> None:
    async with databases.postgres.engine.begin() as connection:
        await connection.execute(text("CREATE TABLE kh_document (id bigint primary key)"))
        await connection.execute(text("INSERT INTO kh_document VALUES (123)"))
    with pytest.raises(RuntimeError, match="unversioned"):
        await databases.migrate()
    async with databases.postgres.engine.connect() as connection:
        assert await connection.scalar(text("SELECT id FROM kh_document")) == 123
        assert (
            await connection.run_sync(lambda sync: inspect(sync).has_table("alembic_version"))
            is False
        )


async def test_database_enforces_content_link_unique_and_required(storage: Databases) -> None:
    async with storage.postgres.engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO kh_document(id,title,content_id) VALUES(1,'a','x')")
        )
    for values in ("(2,'b','x')", "(3,'b',NULL)"):
        with pytest.raises(IntegrityError):
            async with storage.postgres.engine.begin() as connection:
                await connection.execute(
                    text(f"INSERT INTO kh_document(id,title,content_id) VALUES{values}")
                )
