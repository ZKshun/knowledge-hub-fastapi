from datetime import UTC, datetime
from uuid import UUID

from bson import ObjectId
from sqlalchemy import select

from knowledge_hub.modules.documents.infrastructure.document_row import DocumentRow
from knowledge_hub.modules.documents.infrastructure.operation_row import OperationRow
from scripts.init_mongo_indexes import initialize_indexes
from scripts.legacy_v1.database import BIGINT_COLUMNS


async def seed_state(storage, state):
    async with storage.postgres.sessions.begin() as session:
        for source in state["postgres"]:
            values = dict(source)
            for key in BIGINT_COLUMNS:
                if values[key] is not None:
                    values[key] = int(values[key])
            for key in ("created_at", "updated_at", "publish_time"):
                if values[key] is not None:
                    values[key] = datetime.fromisoformat(values[key])
            session.add(DocumentRow(**values))
    await initialize_indexes(storage.collection)
    for source in state["mongo"]:
        values = dict(source)
        values["_id"] = ObjectId(values["_id"])
        for key in ("createdAt", "updatedAt"):
            values[key] = datetime.fromisoformat(values[key]).replace(tzinfo=UTC)
        await storage.collection.insert_one(values)


def encode(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.replace(tzinfo=None).isoformat(timespec="microseconds")
    return value


async def snapshot(storage):
    async with storage.postgres.sessions() as session:
        rows = await session.scalars(select(DocumentRow).order_by(DocumentRow.id))
        postgres = [
            {
                column.name: str(value)
                if column.name in BIGINT_COLUMNS and value is not None
                else encode(value)
                for column in DocumentRow.__table__.columns
                for value in [getattr(row, column.name)]
            }
            for row in rows
        ]
        operations = {row.operation_id: row for row in await session.scalars(select(OperationRow))}
    mongo = []
    async for raw in storage.collection.find().sort("_id", 1):
        row = {key: encode(value) for key, value in raw.items()}
        operation_id = row.pop("operationId", None)
        operation = None
        if operation_id is not None:
            rollback = operation_id.startswith("rollback:")
            key = operation_id.removeprefix("rollback:")
            assert str(UUID(key)) == key
            operation = operations[key]
            assert str(operation.document_id) == row["documentId"]
            assert operation.snapshot["content_id"] == row["_id"]
            if rollback:
                assert operation.state == "compensated"
        if "creationFence" in row:
            assert row["creationFence"] is True and operation is not None
            assert operation.operation_type == "create" and operation.state == "compensated"
            assert row["deleted"] is True and row["version"] == 1
            assert row["content"] == row["contentSummary"] == "" and row["contentLength"] == 0
            assert not any(item["id"] == row["documentId"] for item in postgres)
            continue
        mongo.append(row)
    return {"postgres": postgres, "mongo": mongo}
