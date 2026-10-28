import argparse
import asyncio
from pathlib import Path
from typing import cast

from pymongo.asynchronous.collection import AsyncCollection

from knowledge_hub.core.config import Settings
from knowledge_hub.integrations.mongodb.client import MongoDatabase
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord


async def initialize_indexes(collection: AsyncCollection[DocumentContentRecord]) -> None:
    await collection.create_index("documentId", unique=True, name="documentId_1")
    await collection.create_index("deleted", name="deleted_1")


async def _run(env_file: Path | None) -> None:
    mongo = MongoDatabase(Settings(_env_file=env_file))
    try:
        collection = cast(
            AsyncCollection[DocumentContentRecord],
            mongo.database.get_collection("document_content"),
        )
        await initialize_indexes(collection)
        print("document_content: indexes ready")
    finally:
        await mongo.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize v1 MongoDB indexes without dropping data"
    )
    parser.add_argument("--env-file", type=Path, default=None)
    args = parser.parse_args()
    asyncio.run(_run(args.env_file))


if __name__ == "__main__":
    main()
