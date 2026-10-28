from datetime import datetime
from typing import Any

import psycopg
from bson import ObjectId
from psycopg.rows import dict_row
from pymongo import MongoClient

from scripts.legacy_v1.guards import TEST_DATABASE, validate_database_targets

BIGINT_COLUMNS = {"id", "category_id", "team_id", "author_id", "create_by", "update_by"}


class LegacyDatabase:
    def __init__(self, postgres_dsn: str, mongo_uri: str) -> None:
        validate_database_targets(postgres_dsn, mongo_uri)
        self.postgres_dsn = postgres_dsn
        self.mongo: MongoClient[dict[str, Any]] = MongoClient(
            mongo_uri, serverSelectionTimeoutMS=5000
        )
        self.collection = self.mongo[TEST_DATABASE]["document_content"]

    def reset(self) -> None:
        with psycopg.connect(self.postgres_dsn) as connection:
            database = connection.execute("SELECT current_database()").fetchone()
            if database != (TEST_DATABASE,):
                raise ValueError("Unexpected database; refusing test reset")
            connection.execute("TRUNCATE TABLE kh_document")
        self.disable_failure()
        self.collection.delete_many({})
        index = self.collection.index_information().get("documentId_1")
        if index and not index.get("unique"):
            self.collection.drop_index("documentId_1")
        self.collection.create_index("documentId", unique=True)
        self.collection.create_index("deleted")

    def snapshot(self) -> dict[str, object]:
        with psycopg.connect(self.postgres_dsn, row_factory=dict_row) as connection:
            rows = connection.execute("SELECT * FROM kh_document ORDER BY id").fetchall()
        sql_rows = [
            {
                key: str(value) if key in BIGINT_COLUMNS and value is not None else encode(value)
                for key, value in row.items()
            }
            for row in rows
        ]
        mongo_rows = [
            {key: encode(value) for key, value in row.items()}
            for row in self.collection.find().sort("_id", 1)
        ]
        return {"postgres": sql_rows, "mongo": mongo_rows}

    def remove_content(self, document_id: str) -> None:
        self.collection.delete_one({"documentId": document_id})

    def seed_creation_tie(self, document_ids: list[str]) -> None:
        with psycopg.connect(self.postgres_dsn) as connection:
            cursor = connection.execute(
                "UPDATE kh_document SET created_at = '2099-01-01 00:00:00' "
                "WHERE id = ANY(%s::bigint[])",
                (document_ids,),
            )
            if cursor.rowcount != len(document_ids):
                raise ValueError("Tie fixture did not update exactly the expected test documents")

    def fail_next_mongo_command(self, command: str) -> None:
        self.mongo.admin.command(
            {
                "configureFailPoint": "failCommand",
                "mode": {"times": 1},
                "data": {"failCommands": [command], "errorCode": 2, "errorLabels": []},
            }
        )

    def disable_failure(self) -> None:
        self.mongo.admin.command({"configureFailPoint": "failCommand", "mode": "off"})

    def close(self) -> None:
        self.disable_failure()
        self.mongo.close()


def encode(value: object) -> object:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds")
    return value
