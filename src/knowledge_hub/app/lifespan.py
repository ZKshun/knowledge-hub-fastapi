from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import cast

from fastapi import FastAPI
from pymongo.asynchronous.collection import AsyncCollection
from sqlalchemy import text

from knowledge_hub.core.clock import SystemClock
from knowledge_hub.core.config import Settings
from knowledge_hub.core.ids import SnowflakeIdGenerator
from knowledge_hub.core.logging import configure_logging
from knowledge_hub.integrations.mongodb.client import MongoDatabase
from knowledge_hub.integrations.postgres.database import PostgresDatabase
from knowledge_hub.modules.documents.api.dependencies import DocumentServices
from knowledge_hub.modules.documents.application.ports import DocumentStore
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord
from knowledge_hub.modules.documents.infrastructure.document_store import PostgresMongoDocumentStore


@asynccontextmanager
async def application_lifespan(
    app: FastAPI,
    settings: Settings | None,
    document_store: DocumentStore | None,
) -> AsyncIterator[None]:
    config = settings if settings is not None else Settings()
    configure_logging()
    clock = SystemClock()
    async with AsyncExitStack() as resources:
        if document_store is None:
            postgres = PostgresDatabase(config)
            resources.push_async_callback(postgres.close)
            mongo = MongoDatabase(config)
            resources.push_async_callback(mongo.close)
            async with postgres.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            await mongo.database.command("ping")
            collection = cast(
                AsyncCollection[DocumentContentRecord],
                mongo.database.get_collection("document_content"),
            )
            document_store = PostgresMongoDocumentStore(postgres, collection)
        app.state.document_services = DocumentServices(
            store=document_store,
            ids=SnowflakeIdGenerator(
                worker_id=config.snowflake_worker_id, offset_ms=config.snowflake_offset, clock=clock
            ),
            clock=clock,
        )
        try:
            yield
        finally:
            del app.state.document_services
