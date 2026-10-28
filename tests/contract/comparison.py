from collections.abc import Mapping
from itertools import groupby


def normalize_response(payload: object, bindings: dict[str, str]) -> object:
    """Replace only explicitly bound scalar strings; retain the original input."""
    if isinstance(payload, str):
        return bindings.get(payload, payload)
    if isinstance(payload, list):
        return [normalize_response(value, bindings) for value in payload]
    if isinstance(payload, Mapping):
        return {key: normalize_response(value, bindings) for key, value in payload.items()}
    return payload


def assert_equivalent(expected: object, actual: object) -> None:
    _compare(expected, actual, "$")


def assert_page_with_ties_equivalent(expected: object, actual: object) -> None:
    expected_groups, expected_page = _order_tie_groups(expected)
    actual_groups, actual_page = _order_tie_groups(actual)
    _compare(expected_groups, actual_groups, "$.items.createdAt groups")
    assert_equivalent(expected_page, actual_page)


def _order_tie_groups(payload: object) -> tuple[list[str], dict[str, object]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise AssertionError("$: expected a document page with an items list")
    rows: list[dict[str, object]] = []
    for row in payload["items"]:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("id"), str)
            or not isinstance(row.get("createdAt"), str)
        ):
            raise AssertionError("$.items: expected string id and createdAt")
        rows.append(dict(row))
    groups = [(key, list(group)) for key, group in groupby(rows, lambda row: str(row["createdAt"]))]
    page: dict[str, object] = dict(payload)
    page["items"] = [
        row for _, group in groups for row in sorted(group, key=lambda row: str(row["id"]))
    ]
    return [key for key, _ in groups], page


def _compare(expected: object, actual: object, path: str) -> None:
    if type(expected) is not type(actual):
        raise AssertionError(f"{path}: type {type(expected).__name__} != {type(actual).__name__}")
    if isinstance(expected, dict) and isinstance(actual, dict):
        if expected.keys() != actual.keys():
            raise AssertionError(f"{path}: fields {sorted(expected)} != {sorted(actual)}")
        for key, value in expected.items():
            _compare(value, actual[key], f"{path}.{key}")
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            raise AssertionError(f"{path}: length {len(expected)} != {len(actual)}")
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            _compare(left, right, f"{path}[{index}]")
    elif expected != actual:
        raise AssertionError(f"{path}: {expected!r} != {actual!r}")
