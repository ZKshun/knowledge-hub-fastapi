import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kh_document",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content_id", sa.String(), nullable=False),
        sa.Column("summary", sa.String()),
        sa.Column("category_id", sa.BigInteger()),
        sa.Column("team_id", sa.BigInteger()),
        sa.Column("author_id", sa.BigInteger()),
        sa.Column("cover_image", sa.String()),
        sa.Column("tags", sa.String()),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("remark", sa.String()),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("like_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("favourite_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("publish_time", sa.DateTime(timezone=False)),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("create_by", sa.BigInteger()),
        sa.Column("update_by", sa.BigInteger()),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("content_id", name="kh_document_content_id_key"),
    )
    op.create_table(
        "kh_document_operation",
        sa.Column("operation_id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("operation_type", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("expected_version", sa.Integer()),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "operation_type IN ('create','update','delete')", name="ck_operation_kind"
        ),
        sa.CheckConstraint(
            "state IN ('prepared','completed','compensation_pending','compensated')",
            name="ck_operation_state",
        ),
        sa.CheckConstraint(
            "expected_version IS NULL OR expected_version >= 1", name="ck_expected_version"
        ),
    )
    op.create_index(
        "ix_pending_document",
        "kh_document_operation",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('prepared','compensation_pending')"),
    )
    op.create_index("ix_operation_pending", "kh_document_operation", ["state", "created_at"])


def downgrade() -> None:
    op.drop_table("kh_document_operation")
    op.drop_table("kh_document")
