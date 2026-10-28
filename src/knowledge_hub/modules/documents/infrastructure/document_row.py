from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_hub.integrations.postgres.database import Base


class DocumentRow(Base):
    __tablename__ = "kh_document"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String)
    content_id: Mapped[str] = mapped_column(String, unique=True)
    summary: Mapped[str | None] = mapped_column(String)
    category_id: Mapped[int | None] = mapped_column(BigInteger)
    team_id: Mapped[int | None] = mapped_column(BigInteger)
    author_id: Mapped[int | None] = mapped_column(BigInteger)
    cover_image: Mapped[str | None] = mapped_column(String)
    tags: Mapped[str | None] = mapped_column(String)
    status: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    remark: Mapped[str | None] = mapped_column(String)
    view_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    like_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    comment_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    favourite_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    word_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    publish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    is_public: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=text("now()")
    )
    create_by: Mapped[int | None] = mapped_column(BigInteger)
    update_by: Mapped[int | None] = mapped_column(BigInteger)
    deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
