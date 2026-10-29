from datetime import UTC
from typing import Any

from pymongo import AsyncMongoClient

from knowledge_hub.core.config import Settings


class MongoDatabase:
    def __init__(self, settings: Settings) -> None:
        self.client: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(
            settings.mongo_uri.get_secret_value(),
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            tz_aware=True,
            tzinfo=UTC,
        )
        self.database = self.client.get_default_database(default="test")

    async def close(self) -> None:
        await self.client.close()
