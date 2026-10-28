from datetime import UTC, datetime

from bson import ObjectId
from sqlalchemy.sql.elements import Cast

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.integrations.postgres.identifiers import bigint_parameter
from knowledge_hub.modules.documents.domain.document import Document, DocumentStatus
from knowledge_hub.modules.documents.domain.text_metrics import (
    build_content_summary,
    content_length,
)
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord
from knowledge_hub.modules.documents.infrastructure.document_row import DocumentRow
from knowledge_hub.modules.documents.infrastructure.operation_row import OperationRow
from knowledge_hub.modules.documents.infrastructure.operation_types import OperationRecord


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def bson_string(value: str) -> str:
    # Node's BSON UTF-8 encoder replaces unpaired UTF-16 surrogates with U+FFFD.
    return value.encode("utf-16-le", errors="surrogatepass").decode("utf-16-le", errors="replace")


def optional_id(value: int | None) -> str | None:
    return str(value) if value is not None else None


def to_operation_record(row: OperationRow) -> OperationRecord:
    return OperationRecord(
        operation_id=row.operation_id,
        document_id=DocumentId(str(row.document_id)),
        operation_type=row.operation_type,
        state=row.state,
        expected_version=row.expected_version,
        snapshot=row.snapshot,
        last_error=row.last_error,
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
    )


def to_document(row: DocumentRow) -> Document:
    return Document(
        id=DocumentId(str(row.id)),
        title=row.title,
        content_id=row.content_id,
        summary=row.summary,
        category_id=optional_id(row.category_id),
        team_id=optional_id(row.team_id),
        author_id=optional_id(row.author_id),
        cover_image=row.cover_image,
        tags=row.tags,
        status=DocumentStatus(row.status),
        remark=row.remark,
        view_count=row.view_count,
        like_count=row.like_count,
        comment_count=row.comment_count,
        favourite_count=row.favourite_count,
        word_count=row.word_count,
        publish_time=as_utc(row.publish_time) if row.publish_time else None,
        is_public=row.is_public,
        created_at=as_utc(row.created_at),
        updated_at=as_utc(row.updated_at),
        create_by=optional_id(row.create_by),
        update_by=optional_id(row.update_by),
        deleted=row.deleted,
    )


def _bigint(value: str | None) -> Cast[int] | None:
    return bigint_parameter(value) if value is not None else None


def to_row(document: Document) -> DocumentRow:
    if document.content_id is None:
        raise ValueError("Persisted documents require a content ID")
    return DocumentRow(
        id=int(document.id),
        title=document.title,
        content_id=document.content_id,
        summary=document.summary,
        category_id=_bigint(document.category_id),
        team_id=_bigint(document.team_id),
        author_id=_bigint(document.author_id),
        cover_image=document.cover_image,
        tags=document.tags,
        status=int(document.status),
        remark=document.remark,
        view_count=document.view_count,
        like_count=document.like_count,
        comment_count=document.comment_count,
        favourite_count=document.favourite_count,
        word_count=document.word_count,
        publish_time=as_utc(document.publish_time).replace(tzinfo=None)
        if document.publish_time
        else None,
        is_public=document.is_public,
        created_at=as_utc(document.created_at).replace(tzinfo=None),
        updated_at=as_utc(document.updated_at).replace(tzinfo=None),
        create_by=_bigint(document.create_by),
        update_by=_bigint(document.update_by),
        deleted=document.deleted,
    )


def make_content_record(
    document_id: DocumentId,
    content: str,
    *,
    now: datetime,
    summary: str | None = None,
    operation_id: str | None = None,
) -> DocumentContentRecord:
    record: DocumentContentRecord = {
        "_id": ObjectId(),
        "documentId": str(document_id),
        "content": bson_string(content),
        "contentLength": content_length(content),
        "contentSummary": bson_string(
            summary if summary is not None else build_content_summary(content)
        ),
        "version": 1,
        "deleted": False,
        "createdAt": as_utc(now),
        "updatedAt": as_utc(now),
    }
    if operation_id is not None:
        record["operationId"] = operation_id
    return record
