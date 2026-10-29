from knowledge_hub.core.identifiers import DocumentId


class ApplicationError(Exception):
    """Application failures; transport adapters own status codes and response bodies."""


class DocumentNotFound(ApplicationError):
    def __init__(self, document_id: DocumentId) -> None:
        self.document_id = document_id
        super().__init__(f"Document {document_id} not found")


class DocumentContentNotFound(ApplicationError):
    def __init__(self, content_id: str) -> None:
        self.content_id = content_id
        super().__init__(f"Document content {content_id} not found")


class InvalidDocumentChange(ApplicationError, ValueError):
    pass


class DocumentOperationPending(ApplicationError):
    def __init__(self, document_id: DocumentId) -> None:
        self.document_id = document_id
        super().__init__(f"Document {document_id} has an unresolved operation")


class DocumentAlreadyExists(ApplicationError):
    def __init__(self, document_id: DocumentId) -> None:
        super().__init__(f"Document {document_id} already exists")


class OperationRecoveryError(ApplicationError):
    pass


class InvalidDocumentContent(ApplicationError):
    pass


class IdGenerationError(ApplicationError):
    pass


class ClockRegression(IdGenerationError):
    pass


class InvalidClock(IdGenerationError):
    pass


class SequenceExhausted(IdGenerationError):
    pass


class TimestampOutOfRange(IdGenerationError):
    pass
