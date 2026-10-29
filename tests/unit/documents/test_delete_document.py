import pytest

from knowledge_hub.core.errors import DocumentNotFound
from knowledge_hub.core.identifiers import DocumentId
from knowledge_hub.modules.documents.application.commands.delete_document import delete_document


class DeletingStore:
    deleted = False

    async def soft_delete(self, document_id: DocumentId) -> None:
        if self.deleted or document_id != "101":
            raise DocumentNotFound(document_id)
        self.deleted = True


async def test_delete_returns_legacy_result_and_repeat_raises_not_found() -> None:
    store = DeletingStore()
    result = await delete_document(DocumentId("101"), store=store)
    assert result.document_id == "101" and result.deleted is True
    with pytest.raises(DocumentNotFound, match="Document 101 not found"):
        await delete_document(DocumentId("101"), store=store)


async def test_missing_delete_is_not_success() -> None:
    with pytest.raises(DocumentNotFound, match="Document 404 not found"):
        await delete_document(DocumentId("404"), store=DeletingStore())
