import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from pymongo.asynchronous.collection import AsyncCollection
from sqlalchemy import text
from sqlalchemy.engine import Connection

from knowledge_hub.core.config import Settings
from knowledge_hub.integrations.mongodb.client import MongoDatabase
from knowledge_hub.integrations.postgres.database import PostgresDatabase
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord
from scripts.legacy_v1.guards import validate_database_targets
from scripts.legacy_v1.runner import MONGO_URI, POSTGRES_DSN

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Databases:
    postgres: PostgresDatabase
    mongo: MongoDatabase
    collection: AsyncCollection[DocumentContentRecord]
    schema: str

    def migration(self, connection: Connection, target: str = "head") -> None:
        config = Config(str(ROOT / "alembic.ini"))
        config.attributes.update(connection=connection, schema=self.schema)
        if target == "base":
            command.downgrade(config, target)
        else:
            command.upgrade(config, target)

    async def migrate(self, target: str = "head") -> None:
        async with self.postgres.engine.begin() as connection:
            await connection.run_sync(lambda sync: self.migration(sync, target))


@pytest.fixture
async def databases() -> AsyncIterator[Databases]:
    if os.environ.get("KH_RUN_STORAGE_DB_TESTS") != "1":
        pytest.skip("Requires isolated databases and KH_RUN_STORAGE_DB_TESTS=1")
    validate_database_targets(POSTGRES_DSN, MONGO_URI)
    settings = Settings(
        _env_file=None,
        port=8000,
        postgres_host="127.0.0.1",
        postgres_port=55432,
        postgres_user="kh_test",
        postgres_password="local-contract-only",
        postgres_db="knowledge_hub_fastapi_test",
        mongo_uri=MONGO_URI,
        snowflake_worker_id=1,
        snowflake_offset=1704067200000,
    )
    admin = PostgresDatabase(settings)
    schema = f"kh_t3_{uuid4().hex}"
    async with admin.engine.begin() as connection:
        assert await connection.scalar(text("SELECT current_database()")) == settings.postgres_db
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    postgres = PostgresDatabase(settings, schema=schema)
    mongo = MongoDatabase(settings)
    collection = cast(
        AsyncCollection[DocumentContentRecord],
        mongo.database.get_collection(f"document_content_{schema}"),
    )
    try:
        yield Databases(postgres, mongo, collection, schema)
    finally:
        await mongo.database.drop_collection(collection.name)
        await mongo.close()
        await postgres.close()
        async with admin.engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.close()


@pytest.fixture
async def storage(databases: Databases) -> Databases:
    await databases.migrate()
    return databases
