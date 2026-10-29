from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection

from knowledge_hub.core.errors import OperationRecoveryError
from knowledge_hub.modules.documents.infrastructure.content_record import DocumentContentRecord
from knowledge_hub.modules.documents.infrastructure.mutation_plan import MutationPlan


class ContentMutations:
    def __init__(self, collection: AsyncCollection[DocumentContentRecord]) -> None:
        self.collection = collection

    async def apply(self, plan: MutationPlan) -> None:
        operation = plan.operation
        before = operation.snapshot["before"]
        if not isinstance(before, dict):
            return
        changes = {**plan.changes, "operationId": operation.operation_id}
        result = await self.collection.update_one(
            {
                "_id": ObjectId(str(operation.snapshot["content_id"])),
                "documentId": str(operation.document_id),
                "version": operation.expected_version,
                "operationId": before["operationId"],
                "deleted": before["deleted"],
            },
            {"$set": changes},
        )
        if result.matched_count != 1:
            raise OperationRecoveryError("Document body changed outside the operation fence")
