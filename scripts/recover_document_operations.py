import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import cast

from pymongo.asynchronous.collection import AsyncCollection

from knowledge_hub.core.config import Settings
from knowledge_hub.integrations.mongodb.client import MongoDatabase
from knowledge_hub.integrations.postgres.database import PostgresDatabase
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord
from knowledge_hub.modules.documents.infrastructure.operation_types import RecoveryReport
from knowledge_hub.modules.documents.infrastructure.recovery import RecoveryService


async def run_recovery(
    settings: Settings, *, schema: str, collection_name: str, limit: int
) -> RecoveryReport:
    postgres = PostgresDatabase(settings, schema=schema)
    try:
        mongo = MongoDatabase(settings)
        try:
            collection = cast(
                AsyncCollection[DocumentContentRecord],
                mongo.database.get_collection(collection_name),
            )
            return await RecoveryService(postgres, collection).recover_pending(limit=limit)
        finally:
            await mongo.close()
    finally:
        await postgres.close()


def batch_limit(value: str) -> int:
    limit = int(value)
    if not 1 <= limit <= 1000:
        raise argparse.ArgumentTypeError("limit must be between 1 and 1000")
    return limit


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile pending v1 document operations")
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--schema", default="public")
    parser.add_argument("--collection", default="document_content")
    parser.add_argument("--limit", type=batch_limit, default=100)
    args = parser.parse_args()
    try:
        report = asyncio.run(
            run_recovery(
                Settings(_env_file=args.env_file),
                schema=args.schema,
                collection_name=args.collection,
                limit=args.limit,
            )
        )
    except Exception as error:
        # Driver exception text can contain private SQL parameters or credentials.
        print(type(error).__name__, file=sys.stderr)
        return 2
    print(json.dumps(asdict(report)))
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
