from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, model_validator
from pydantic.alias_generators import to_camel

from knowledge_hub.modules.documents.api.query_numbers import validate_query
from knowledge_hub.modules.documents.api.validation import validate_body

type StatusInput = StrictInt | Literal["Draft", "Published", "Archived"] | None


class DocumentFields(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid")
    title: StrictStr | None = None
    content: StrictStr | None = None
    summary: StrictStr | None = None
    category_id: StrictStr | None = None
    team_id: StrictStr | None = None
    author_id: StrictStr | None = None
    cover_image: StrictStr | None = None
    tags: StrictStr | None = None
    status: StatusInput = None
    remark: StrictStr | None = None
    is_public: StrictBool | None = None


class CreateDocumentRequest(DocumentFields):
    title: StrictStr
    content: StrictStr
    create_by: StrictStr | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_input(cls, value: object) -> dict[str, object]:
        return validate_body(value, partial=False)


class UpdateDocumentRequest(DocumentFields):
    update_by: StrictStr | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_input(cls, value: object) -> dict[str, object]:
        return validate_body(value, partial=True)


class DocumentQueryRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra="forbid")
    title: StrictStr | None = None
    category_id: StrictStr | None = None
    team_id: StrictStr | None = None
    author_id: StrictStr | None = None
    status: StrictInt | None = None
    page: StrictInt = Field(default=1, json_schema_extra={"minimum": 1})
    page_size: StrictInt = Field(default=20, json_schema_extra={"minimum": 1, "maximum": 100})

    @model_validator(mode="before")
    @classmethod
    def validate_input(cls, value: object) -> dict[str, object]:
        return validate_query(value)
