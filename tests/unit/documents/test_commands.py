from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime

import pytest

from knowledge_hub.core.errors import (
    DocumentContentNotFound,
    DocumentNotFound,
    InvalidDocumentChange,
)
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.domain.commands import (
    CreateDocumentCommand,
    DocumentMutation,
    DocumentQuery,
    UpdateDocumentCommand,
)
from knowledge_hub.modules.documents.domain.document import Document, DocumentDetail, DocumentStatus


def test_update_keeps_explicit_null_and_same_content() -> None:
    assert dict(UpdateDocumentCommand(changes={}).changes) == {}
    command = UpdateDocumentCommand(changes={"summary": None, "content": "unchanged"})
    assert command.changes == {"summary": None, "content": "unchanged"}
    assert "title" not in command.changes


def test_update_owns_an_immutable_snapshot() -> None:
    supplied = {"title": "initial"}
    command = UpdateDocumentCommand(changes=supplied)
    supplied["title"] = "later"
    assert command.changes["title"] == "initial"
    with pytest.raises(TypeError):
        command.changes["title"] = "other"  # type: ignore[index]


@pytest.mark.parametrize("field", ["create_by", "deleted", "content_id", "unknown", "isPublic"])
def test_update_rejects_fields_outside_internal_command(field: str) -> None:
    with pytest.raises(InvalidDocumentChange, match=field):
        UpdateDocumentCommand(changes={field: "value"})


def test_mutation_retains_presence_even_when_target_is_identical() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    document = Document(id=DocumentId("123"), title="Example", created_at=now, updated_at=now)
    detail = DocumentDetail(document=document, content="unchanged")
    mutation = DocumentMutation(target=detail, provided_fields=frozenset({"content"}))
    assert mutation.target == detail
    assert mutation.provided_fields == {"content"}
    assert replace(document, title="Updated").id == "123"
    with pytest.raises(FrozenInstanceError):
        document.title = "mutated"  # type: ignore[misc]


def test_create_retains_null_for_use_case_defaults() -> None:
    command = CreateDocumentCommand(title="", content="", status=None, is_public=None)
    assert command.title == command.content == ""
    assert command.status is None and command.is_public is None
    assert command.summary is None
    assert list(DocumentStatus) == [0, 1, 2]


def test_query_accepts_any_integer_status_as_legacy_does() -> None:
    query = DocumentQuery(status=999)
    assert query.status == 999
    assert query.page == 1 and query.page_size == 20
    assert DocumentQuery(page_size=100).page_size == 100


@pytest.mark.parametrize(
    "values", [{"page": 0}, {"page_size": 0}, {"page_size": 101}, {"page": True}, {"status": True}]
)
def test_query_rejects_invalid_normalized_parameters(values: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        DocumentQuery(**values)


def test_business_errors_keep_legacy_messages_without_http_binding() -> None:
    assert str(DocumentNotFound(DocumentId("123"))) == "Document 123 not found"
    assert str(DocumentContentNotFound("abc")) == "Document content abc not found"
