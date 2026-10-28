import pytest

from tests.contract.comparison import assert_equivalent, normalize_response


@pytest.mark.parametrize("actual", [9007199254740993, None])
def test_comparison_preserves_id_type(actual: object) -> None:
    with pytest.raises(AssertionError, match=r"\$\.id"):
        assert_equivalent({"id": "9007199254740993"}, {"id": actual})


@pytest.mark.parametrize("actual", [1, 1.0])
def test_comparison_does_not_treat_bool_as_number(actual: object) -> None:
    with pytest.raises(AssertionError, match=r"\$\.deleted"):
        assert_equivalent({"deleted": True}, {"deleted": actual})


def test_comparison_preserves_field_presence() -> None:
    with pytest.raises(AssertionError, match=r"\$"):
        assert_equivalent({"summary": None}, {})


def test_comparison_preserves_list_order_and_reports_nested_path() -> None:
    with pytest.raises(AssertionError, match=r"\$\.items\[0\]\.title"):
        assert_equivalent(
            {"items": [{"title": "first"}, {"title": "second"}]},
            {"items": [{"title": "second"}, {"title": "first"}]},
        )


def test_comparison_accepts_object_key_reordering() -> None:
    assert_equivalent({"page": 1, "items": []}, {"items": [], "page": 1})


def test_normalization_reuses_explicit_bindings_across_nested_responses() -> None:
    bindings = {"9007199254740993": "@document:alpha"}
    actual = normalize_response(
        {"id": "9007199254740993", "items": [{"documentId": "9007199254740993"}]},
        bindings,
    )
    assert actual == {"id": "@document:alpha", "items": [{"documentId": "@document:alpha"}]}


def test_normalization_never_coerces_numbers_or_rewrites_arbitrary_text() -> None:
    payload = {"count": 123, "content": "document 123", "other": "456"}
    assert normalize_response(payload, {"123": "@id"}) == payload


def test_normalization_preserves_null_and_unbound_timestamps() -> None:
    payload = {"summary": None, "createdAt": "2026-10-28T00:00:00.000Z"}
    assert normalize_response(payload, {}) == payload


def test_normalization_does_not_modify_the_recorded_input() -> None:
    payload = {"id": "123", "items": [{"id": "123"}]}
    normalize_response(payload, {"123": "@id"})
    assert payload == {"id": "123", "items": [{"id": "123"}]}
