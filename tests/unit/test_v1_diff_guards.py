from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from tests.support.v1_compare import compare_evidence

START = datetime(2026, 1, 1, tzinfo=UTC)
END = START + timedelta(seconds=1)


def examples():
    expected = {
        "response": {
            "status": 201,
            "contentType": "application/json; charset=utf-8",
            "body": {
                "id": "101",
                "contentId": "a" * 24,
                "createdAt": "2020-01-01T00:00:00.123Z",
                "updatedAt": "2020-01-01T00:00:00.123Z",
                "publishTime": None,
            },
        },
        "state": {
            "postgres": [
                {
                    "id": "101",
                    "content_id": "a" * 24,
                    "created_at": "2020-01-01T00:00:00.123456",
                    "updated_at": "2020-01-01T00:00:00.123456",
                    "publish_time": None,
                }
            ],
            "mongo": [],
        },
    }
    actual = deepcopy(expected)
    for field in ("createdAt", "updatedAt"):
        actual["response"]["body"][field] = "2026-01-01T00:00:00.123Z"
    for field in ("created_at", "updated_at"):
        actual["state"]["postgres"][0][field] = "2026-01-01T00:00:00.123456"
    return expected, actual


def compare(expected, actual, before=None):
    compare_evidence(
        expected,
        actual,
        before if before is not None else {"postgres": [], "mongo": []},
        started=START,
        finished=END,
    )


def test_new_timestamp_values_may_differ_within_request_but_structure_stays_strict():
    expected, actual = examples()
    compare(expected, actual)


def test_timestamp_normalization_rejects_wrong_api_sql_association():
    expected, actual = examples()
    actual["response"]["body"]["updatedAt"] = "2026-01-01T00:00:00.999Z"
    with pytest.raises(AssertionError, match="association"):
        compare(expected, actual)


def test_normalization_cannot_hide_changes_to_unchanged_timestamps():
    expected, actual = examples()
    with pytest.raises(AssertionError):
        compare(expected, actual, deepcopy(expected["state"]))


@pytest.mark.parametrize(
    "timestamp",
    ["2026-01-01T00:00:00.123", "2026-01-01T00:00:00.123456Z", "2020-01-01T00:00:00.123456"],
)
def test_normalization_rejects_changed_precision_zone_or_stale_time(timestamp):
    expected, actual = examples()
    actual["state"]["postgres"][0]["updated_at"] = timestamp
    with pytest.raises(AssertionError):
        compare(expected, actual)


def test_content_id_binding_does_not_hide_broken_database_association():
    expected, actual = examples()
    expected["state"]["mongo"] = [{"documentId": "101", "_id": "a" * 24}]
    actual["state"]["mongo"] = [{"documentId": "101", "_id": "b" * 24}]
    actual["state"]["postgres"][0]["content_id"] = "c" * 24
    actual["response"]["body"]["contentId"] = "c" * 24
    with pytest.raises(AssertionError):
        compare(expected, actual)


def test_deleted_business_records_cannot_be_ignored():
    expected, actual = examples()
    expected["state"]["mongo"] = [
        {"documentId": "101", "_id": "a" * 24, "deleted": True, "content": "retained"}
    ]
    with pytest.raises(AssertionError, match="Missing mongo"):
        compare(expected, actual)
