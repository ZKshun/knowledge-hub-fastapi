class BodyDecodingError(Exception):
    def __init__(self, status_code: int, message: str, *, error_label: str | None = None) -> None:
        self.status_code = status_code
        self.message = message
        self.error_label = error_label
        super().__init__(message)
