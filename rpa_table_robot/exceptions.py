class TableRobotError(RuntimeError):
    """Base exception for the table robot package."""


class OcrServiceUnavailable(TableRobotError):
    """Raised when the OCR sidecar cannot be reached or is misconfigured."""


class OcrRecognitionError(TableRobotError):
    """Raised when the OCR sidecar rejects or fails a recognition request."""
