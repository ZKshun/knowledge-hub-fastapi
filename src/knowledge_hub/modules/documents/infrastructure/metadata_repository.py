from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.integrations.postgres.identifiers import bigint_parameter
from knowledge_hub.modules.documents.domain.commands import DocumentQuery
from knowledge_hub.modules.documents.domain.document import Document, DocumentPage
from knowledge_hub.modules.documents.infrastructure.document_row import DocumentRow
from knowledge_hub.modules.documents.infrastructure.mappers import to_document


class MetadataRepository:
    async def exists(self, session: AsyncSession, document_id: DocumentId) -> bool:
        return bool(
            await session.scalar(
                select(exists().where(DocumentRow.id == bigint_parameter(document_id)))
            )
        )

    async def get(self, session: AsyncSession, document_id: DocumentId) -> Document | None:
        row = await session.scalar(
            select(DocumentRow).where(
                DocumentRow.id == bigint_parameter(document_id),
                DocumentRow.deleted.is_(False),
            )
        )
        return to_document(row) if row is not None else None

    async def page(self, session: AsyncSession, query: DocumentQuery) -> DocumentPage:
        filters = self._filters(query)
        total = await session.scalar(select(func.count()).select_from(DocumentRow).where(*filters))
        rows = await session.scalars(
            select(DocumentRow)
            .where(*filters)
            .order_by(DocumentRow.created_at.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        return DocumentPage(
            items=tuple(to_document(row) for row in rows),
            total=total or 0,
            page=query.page,
            page_size=query.page_size,
        )

    @staticmethod
    def _filters(query: DocumentQuery) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = [DocumentRow.deleted.is_(False)]
        if query.title:
            filters.append(DocumentRow.title.ilike(f"%{query.title}%"))
        for value, column in (
            (query.category_id, DocumentRow.category_id),
            (query.team_id, DocumentRow.team_id),
            (query.author_id, DocumentRow.author_id),
        ):
            if value:
                filters.append(column == bigint_parameter(value))
        if query.status is not None:
            filters.append(DocumentRow.status == query.status)
        return filters
