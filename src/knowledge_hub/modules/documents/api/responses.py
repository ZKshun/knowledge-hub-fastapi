from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel


class WireModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class DocumentMetadataResponse(WireModel):
    id: str
    title: str
    content_id: str
    summary: str | None
    category_id: str | None
    team_id: str | None
    author_id: str | None
    cover_image: str | None
    tags: str | None
    status: int
    remark: str | None
    view_count: int
    like_count: int
    comment_count: int
    favourite_count: int
    word_count: int
    publish_time: datetime | None
    is_public: bool
    created_at: datetime
    updated_at: datetime
    create_by: str | None
    update_by: str | None
    deleted: bool

    @field_serializer("created_at", "updated_at", "publish_time", when_used="json")
    def serialize_time(self, value: datetime | None) -> str | None:
        return (
            value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            if value
            else None
        )


class DocumentResponse(DocumentMetadataResponse):
    content: str


class DocumentPageResponse(WireModel):
    items: list[DocumentMetadataResponse]
    total: int
    page: int
    page_size: int


class DeleteDocumentResponse(WireModel):
    id: str
    deleted: bool


class ErrorResponse(WireModel):
    status_code: int
    message: str | list[str]
    error: str | None = None
