import asyncio
import json
import os
import sys

import pytest

from knowledge_hub.core.identifiers import DocumentId
from tests.integration.documents.conftest import ROOT, Databases
from tests.integration.documents.create_support import ProcessStopped
from tests.integration.documents.mutation_support import change, seeded


async def cli(storage: Databases, *extra: str):
    env = {
        **os.environ,
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "55432",
        "POSTGRES_USER": "kh_test",
        "POSTGRES_PASSWORD": "local-contract-only",
        "POSTGRES_DB": "knowledge_hub_fastapi_test",
        "MONGO_URI": "mongodb://127.0.0.1:57017/knowledge_hub_fastapi_test",
        "SNOWFLAKE_WORKER_ID": "1",
        "SNOWFLAKE_OFFSET": "1704067200000",
    }
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "scripts/recover_document_operations.py",
        "--schema",
        storage.schema,
        "--collection",
        storage.collection.name,
        *extra,
        cwd=ROOT,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), 15)
    return process.returncode, stdout.decode(), stderr.decode()


async def test_cli_recovers_interrupted_mutation_then_idempotently_reports_zero(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = await seeded(storage)
    update = storage.collection.update_one

    async def stopped(*args, **kwargs):
        await update(*args, **kwargs)
        raise ProcessStopped()

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "update_one", stopped)
        with pytest.raises(ProcessStopped):
            await change(store)
    code, stdout, stderr = await cli(storage, "--limit", "100")
    assert code == 0, stderr
    assert json.loads(stdout) == {"completed": 0, "compensated": 1, "failed": 0}
    detail = await store.get(DocumentId("101"))
    assert detail is not None and detail.content == "知识库 hello world"
    code, stdout, stderr = await cli(storage)
    assert code == 0, stderr
    assert json.loads(stdout) == {"completed": 0, "compensated": 0, "failed": 0}


async def test_cli_conflict_exits_nonzero_without_printing_private_content(
    storage: Databases, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = await seeded(storage)

    async def stopped(*args, **kwargs):
        raise ProcessStopped()

    with monkeypatch.context() as patch:
        patch.setattr(storage.collection, "update_one", stopped)
        with pytest.raises(ProcessStopped):
            await change(store)
    await storage.collection.update_one(
        {"documentId": "101"}, {"$set": {"operationId": "foreign", "content": "PRIVATE_SENTINEL"}}
    )
    code, stdout, stderr = await cli(storage)
    assert code == 1 and json.loads(stdout) == {"completed": 0, "compensated": 0, "failed": 1}
    assert "PRIVATE_SENTINEL" not in stdout + stderr


@pytest.mark.parametrize("limit", ["0", "1001", "invalid"])
async def test_cli_rejects_invalid_batch_size(storage: Databases, limit: str) -> None:
    code, stdout, stderr = await cli(storage, "--limit", limit)
    assert code == 2 and stdout == "" and "usage:" in stderr and "--limit" in stderr
