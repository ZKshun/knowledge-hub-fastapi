import os

import pytest

from scripts.legacy_v1.database import LegacyDatabase
from scripts.legacy_v1.runner import MONGO_URI, POSTGRES_DSN

pytestmark = pytest.mark.skipif(
    os.environ.get("KH_RUN_LEGACY_DB_TESTS") != "1",
    reason="Requires the isolated kh-fastapi-v1-test database containers",
)


def test_reset_restores_legacy_unique_index_after_mongoose_autoindex() -> None:
    database = LegacyDatabase(POSTGRES_DSN, MONGO_URI)
    try:
        existing = database.collection.index_information()
        if "documentId_1" in existing:
            database.collection.drop_index("documentId_1")
        database.collection.create_index("documentId")
        database.reset()
        assert database.collection.index_information()["documentId_1"]["unique"] is True
    finally:
        database.close()
