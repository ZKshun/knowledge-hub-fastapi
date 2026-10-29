import re
from copy import deepcopy
from datetime import UTC, datetime, timedelta

from tests.contract.comparison import assert_equivalent, assert_page_with_ties_equivalent

_TIME = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.(?P<fraction>\d+))?(?P<zone>Z|\+00:00)?\Z")
_SQL_TIMES = {"createdAt": "created_at", "updatedAt": "updated_at", "publishTime": "publish_time"}


def compare_evidence(expected, actual, previous, *, started, finished, ties=False):
    left, right = deepcopy(expected), deepcopy(actual)
    _bind_content_ids(left, right, previous)
    original_right_sql = deepcopy(right["state"]["postgres"])
    markers = {}
    for store, id_key, fields in [
        ("postgres", "id", tuple(_SQL_TIMES.values())),
        ("mongo", "documentId", ("createdAt", "updatedAt")),
    ]:
        before = {row[id_key]: row for row in previous[store]}
        actual_rows = {row[id_key]: row for row in right["state"][store]}
        for row in left["state"][store]:
            identifier = row[id_key]
            assert identifier in actual_rows, f"Missing {store} document {identifier}"
            for field in fields:
                value = row.get(field)
                if value is not None and value != before.get(identifier, {}).get(field):
                    _assert_time(value, actual_rows[identifier][field], started, finished)
                    marker = f"@time:{store}:{identifier}:{field}"
                    row[field] = actual_rows[identifier][field] = marker
                    markers[(store, identifier, field)] = marker
    _bind_response_times(
        left["response"]["body"], right["response"]["body"], original_right_sql, markers
    )
    if ties:
        assert_page_with_ties_equivalent(left["response"]["body"], right["response"]["body"])
        left["response"]["body"] = right["response"]["body"] = "@checked-tie-page"
    assert_equivalent(left, right)


def _bind_content_ids(expected, actual, previous):
    before = {row["documentId"]: row for row in previous["mongo"]}
    actual_rows = {row["documentId"]: row for row in actual["state"]["mongo"]}
    bindings = {}
    for row in expected["state"]["mongo"]:
        if row["documentId"] not in before and row["documentId"] in actual_rows:
            actual_id = actual_rows[row["documentId"]]["_id"]
            assert isinstance(actual_id, str) and re.fullmatch("[0-9a-f]{24}", actual_id)
            bindings[actual_id] = row["_id"]
    for row in actual["state"]["mongo"]:
        row["_id"] = bindings.get(row["_id"], row["_id"])
    for row in actual["state"]["postgres"]:
        row["content_id"] = bindings.get(row["content_id"], row["content_id"])
    _map_response_ids(actual["response"]["body"], bindings)


def _map_response_ids(value, bindings):
    if isinstance(value, dict):
        if "contentId" in value:
            value["contentId"] = bindings.get(value["contentId"], value["contentId"])
        for item in value.values():
            _map_response_ids(item, bindings)
    elif isinstance(value, list):
        for item in value:
            _map_response_ids(item, bindings)


def _assert_time(expected, actual, started, finished):
    assert isinstance(actual, str), "Timestamp type changed"
    wanted, got = _TIME.fullmatch(expected), _TIME.fullmatch(actual)
    assert wanted and got, "Invalid timestamp syntax"
    assert len(wanted["fraction"] or "") == len(got["fraction"] or ""), (
        "Timestamp precision changed"
    )
    assert wanted["zone"] == got["zone"], "Timestamp timezone notation changed"
    instant = datetime.fromisoformat(actual).replace(tzinfo=UTC)
    assert started - timedelta(milliseconds=1) <= instant <= finished, (
        "New timestamp outside request"
    )


def _metadata(body):
    if isinstance(body, dict) and "items" in body:
        return body["items"]
    return [body] if isinstance(body, dict) and "createdAt" in body else []


def _bind_response_times(expected, actual, sql_rows, markers):
    actual_rows = {row["id"]: row for row in _metadata(actual)}
    sql = {row["id"]: row for row in sql_rows}
    for row in _metadata(expected):
        identifier = row["id"]
        assert identifier in actual_rows and identifier in sql
        peer = actual_rows[identifier]
        for wire, column in _SQL_TIMES.items():
            persisted = sql[identifier][column]
            serialized = (
                datetime.fromisoformat(persisted)
                .replace(tzinfo=UTC)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
                if persisted is not None
                else None
            )
            assert peer[wire] == serialized, f"Response/SQL {wire} association changed"
            marker = markers.get(("postgres", identifier, column))
            if marker is not None:
                row[wire] = peer[wire] = marker
