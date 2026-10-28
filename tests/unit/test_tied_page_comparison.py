import pytest

from tests.contract.comparison import assert_page_with_ties_equivalent


def page(items: list[dict[str, object]]) -> dict[str, object]:
    return {"items": items, "total": 3, "page": 1, "pageSize": 3}


FIRST = {"id": "1", "title": "first", "createdAt": "2099-01-01T00:00:00.000Z"}
SECOND = {"id": "2", "title": "second", "createdAt": "2099-01-01T00:00:00.000Z"}
OLDER = {"id": "3", "title": "older", "createdAt": "2026-10-28T00:00:00.000Z"}


def test_tie_comparison_allows_only_same_timestamp_group_reordering() -> None:
    assert_page_with_ties_equivalent(page([FIRST, SECOND, OLDER]), page([SECOND, FIRST, OLDER]))


@pytest.mark.parametrize(
    "items",
    [
        [OLDER, FIRST, SECOND],
        [FIRST, OLDER, SECOND],
        [FIRST, {**SECOND, "title": "incorrect"}, OLDER],
        [FIRST, {"id": "2", "createdAt": SECOND["createdAt"]}, OLDER],
    ],
)
def test_tie_comparison_still_rejects_wrong_group_order_or_changed_fields(
    items: list[dict[str, object]],
) -> None:
    with pytest.raises(AssertionError):
        assert_page_with_ties_equivalent(page([FIRST, SECOND, OLDER]), page(items))
