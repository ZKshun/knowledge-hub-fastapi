import asyncio

from alembic import context
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from knowledge_hub.core.config import Settings
from knowledge_hub.integrations.postgres.database import PostgresDatabase

config = context.config


def run_migrations(connection: Connection) -> None:
    schema = config.attributes.get("schema", "public")
    inspector = inspect(connection)
    version_table = inspector.has_table("alembic_version", schema=schema)
    quoted = connection.dialect.identifier_preparer.quote(schema)
    versioned = (
        version_table
        and connection.execute(text(f"SELECT version_num FROM {quoted}.alembic_version")).first()
        is not None
    )
    if not versioned and any(
        inspector.has_table(name, schema=schema)
        for name in (
            "kh_document",
            "kh_document_operation",
        )
    ):
        raise RuntimeError(
            "Refusing migration of unversioned existing tables; explicit baseline required"
        )
    context.configure(connection=connection, version_table_schema=schema, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    database = PostgresDatabase(Settings())
    try:
        async with database.engine.begin() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await database.close()


if context.is_offline_mode():
    raise RuntimeError("Offline migration cannot verify existing tables; use online migration")
elif (connection := config.attributes.get("connection")) is not None:
    run_migrations(connection)
else:
    asyncio.run(run_online())
