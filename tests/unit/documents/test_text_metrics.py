import pytest

from knowledge_hub.modules.documents.domain.text_metrics import (
    build_content_summary,
    content_length,
    count_words,
)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("知识库 hello world", 5),
        ("# 知识库\nhello world 🧠", 7),
        ("", 0),
        (" \t\r\n\ufeff\u00a0", 0),
        ("中，文", 3),
        ("𠀀test", 1),
        ("a\u0085b", 1),
        ("a\u001cb", 1),
        ("a\ufeffb", 2),
        ("\ufeff\u00a0中，文\u2003hello\r\nworld", 5),
    ],
)
def test_count_words_matches_legacy_service(content: str, expected: int) -> None:
    assert count_words(content) == expected


@pytest.mark.parametrize(
    ("content", "expected"),
    [("", 0), ("中文", 2), ("🧠", 2), ("a\ud83e", 2), ("# 知识库\nhello world 🧠", 20)],
)
def test_length_counts_utf16_units(content: str, expected: int) -> None:
    assert content_length(content) == expected


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("a" * 200, "a" * 200),
        ("a" * 201, "a" * 200 + "..."),
        ("🧠" * 100, "🧠" * 100),
        ("a" * 199 + "🧠 tail", "a" * 199 + "\ud83e..."),
        (" \ufeff中\u00a0\t文\r\nhello\u2028world\u3000", "中 文 hello world"),
        ("a\u0085b\u001cb\u200bb", "a\u0085b\u001cb\u200bb"),
        ("\ufeff\u00a0\u2003", ""),
    ],
)
def test_summary_matches_js_whitespace_and_slice(content: str, expected: str) -> None:
    assert build_content_summary(content) == expected


def test_custom_summary_limit_counts_units() -> None:
    assert build_content_summary("🧠abc", 2) == "🧠..."
    assert build_content_summary("text", 0) == "..."
    assert build_content_summary("", 0) == ""


@pytest.mark.parametrize("limit", [-1, True])
def test_invalid_internal_summary_limit_is_rejected(limit: int) -> None:
    with pytest.raises(ValueError):
        build_content_summary("text", limit)
