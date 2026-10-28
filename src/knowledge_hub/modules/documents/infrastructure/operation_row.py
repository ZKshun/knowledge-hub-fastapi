from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_hub.integrations.postgres.database import Base
from knowledge_hub.modules.documents.infrastructure.operation_types import (
    JsonValue,
    OperationKind,
    OperationState,
)


class OperationRow(Base):
    __tablename__ = "kh_document_operation"

    operation_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    document_id: Mapped[int] = mapped_column(BigInteger)
    operation_type: Mapped[OperationKind] = mapped_column(String)
    state: Mapped[OperationState] = mapped_column(String)
    expected_version: Mapped[int | None] = mapped_column(Integer)
    snapshot: Mapped[dict[str, JsonValue]] = mapped_column(JSONB)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
