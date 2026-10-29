import json
from pathlib import Path

import pytest

from tests.support.v1_replay import replay_case

FIXTURES = Path(__file__).parents[1] / "fixtures/contracts/v1"
RECORDS = sorted(FIXTURES.glob("[0-9]*.json"))


@pytest.mark.parametrize("path", RECORDS, ids=lambda path: path.stem)
async def test_original_http_and_database_evidence_matches_fastapi(storage, path):
    index = RECORDS.index(path)
    case = json.loads(path.read_text(encoding="utf-8"))
    previous = (
        json.loads(RECORDS[index - 1].read_text(encoding="utf-8"))["state"]
        if index
        else {"postgres": [], "mongo": []}
    )
    await replay_case(storage, path.stem, case, previous)
