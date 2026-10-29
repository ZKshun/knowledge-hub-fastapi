from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from knowledge_hub.modules.documents.infrastructure.operation_row import OperationRow


async def lock_operation(
    session: AsyncSession, operation_id: str, *, timeout_ms: int = 5000
) -> OperationRow | None:
    if type(timeout_ms) is not int or timeout_ms < 1:
        raise ValueError("timeout_ms must be positive")
    await session.execute(
        text("SELECT set_config('lock_timeout', :timeout, true)"), {"timeout": f"{timeout_ms}ms"}
    )
    # The writer holds this row from before Mongo until SQL commit/rollback. Acquiring
    # it in a fresh transaction proves the previous business transaction has ended.
    return await session.scalar(
        select(OperationRow)
        .where(OperationRow.operation_id == operation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
