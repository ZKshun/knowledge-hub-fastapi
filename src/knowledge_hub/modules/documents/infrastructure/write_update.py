from datetime import UTC, datetime

from knowledge_hub.core.errors import DocumentContentNotFound
from knowledge_hub.modules.documents.domain.commands import DocumentMutation
from knowledge_hub.modules.documents.domain.document import DocumentDetail
from knowledge_hub.modules.documents.domain.text_metrics import (
    build_content_summary,
    content_length,
)
from knowledge_hub.modules.documents.infrastructure.content_record import ContentSnapshot
from knowledge_hub.modules.documents.infrastructure.mappers import node_utf8_string
from knowledge_hub.modules.documents.infrastructure.mutation_plan import MutationPlan, plan_mutation


def plan_update(
    current: DocumentDetail, mutation: DocumentMutation, content: ContentSnapshot | None
) -> MutationPlan:
    if content is not None and content.deleted:
        content = None
    changes: dict[str, object] = {}
    fields, target = mutation.provided_fields, mutation.target
    if "content" in fields:
        if content is None:
            raise DocumentContentNotFound(current.document.content_id or "")
        summary = target.document.summary if "summary" in fields else None
        changes.update(
            content=node_utf8_string(target.content),
            contentLength=content_length(target.content),
            contentSummary=node_utf8_string(
                summary if summary is not None else build_content_summary(target.content)
            ),
            version=content.version + 1,
        )
    elif "summary" in fields and content is not None:
        summary = target.document.summary
        changes["contentSummary"] = node_utf8_string(summary) if summary is not None else None
    if changes:
        now = datetime.now(UTC)
        changes["updatedAt"] = now.replace(microsecond=now.microsecond // 1000 * 1000)
    return plan_mutation("update", current, target, content, changes)
