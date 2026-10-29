from dataclasses import replace
from datetime import UTC, datetime

from knowledge_hub.modules.documents.domain.document import DocumentDetail
from knowledge_hub.modules.documents.infrastructure.content_record import ContentSnapshot
from knowledge_hub.modules.documents.infrastructure.mutation_plan import MutationPlan, plan_mutation


def plan_delete(current: DocumentDetail, content: ContentSnapshot | None) -> MutationPlan:
    now = datetime.now(UTC)
    target = replace(current, document=replace(current.document, deleted=True, updated_at=now))
    changes: dict[str, object] = {}
    if content is not None:
        changes = {
            "deleted": True,
            "updatedAt": now.replace(microsecond=now.microsecond // 1000 * 1000),
        }
    return plan_mutation("delete", current, target, content, changes)
