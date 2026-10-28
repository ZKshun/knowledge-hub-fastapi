from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from knowledge_hub.core.errors import InvalidDocumentChange
from knowledge_hub.modules.documents.domain.document import DocumentDetail, DocumentStatus

type DocumentFieldValue = str | int | bool | None

_UPDATE_FIELDS = frozenset(
    {
        "title",
        "content",
        "summary",
        "category_id",
        "team_id",
        "author_id",
        "cover_image",
        "tags",
        "status",
        "remark",
        "is_public",
        "update_by",
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateDocumentCommand:
    title: str
    content: str
    summary: str | None = None
    category_id: str | None = None
    team_id: str | None = None
    author_id: str | None = None
    cover_image: str | None = None
    tags: str | None = None
    status: DocumentStatus | None = None
    remark: str | None = None
    is_public: bool | None = None
    create_by: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateDocumentCommand:
    changes: Mapping[str, DocumentFieldValue]

    def __post_init__(self) -> None:
        unknown = self.changes.keys() - _UPDATE_FIELDS
        if unknown:
            raise InvalidDocumentChange(
                f"Unsupported document fields: {', '.join(sorted(unknown))}"
            )
        if any(not isinstance(value, (str, int, type(None))) for value in self.changes.values()):
            raise InvalidDocumentChange("Document changes must contain scalar values")
        object.__setattr__(self, "changes", MappingProxyType(dict(self.changes)))


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentMutation:
    target: DocumentDetail
    provided_fields: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "provided_fields", frozenset(self.provided_fields))


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentQuery:
    title: str | None = None
    category_id: str | None = None
    team_id: str | None = None
    author_id: str | None = None
    status: int | None = None
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        if type(self.page) is not int or self.page < 1:
            raise ValueError("page must be an integer >= 1")
        if type(self.page_size) is not int or not 1 <= self.page_size <= 100:
            raise ValueError("page_size must be an integer between 1 and 100")
        if self.status is not None and type(self.status) is not int:
            raise ValueError("status must be an integer")
