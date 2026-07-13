"""Custom exception hierarchy for MediClear AI."""

from __future__ import annotations


class MediClearException(Exception):
    """Base exception for all MediClear AI errors."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AIProviderError(MediClearException):
    """The AI provider returned an error or an unexpected response."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=502)


class AIProviderNotConfiguredError(MediClearException):
    """The requested AI provider is missing required credentials."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"AI provider '{provider}' is not configured. "
            "Please set the required API key in your environment or .env file. "
            "See docs/configuration.md for details.",
            status_code=503,
        )


class UnsupportedModalityError(MediClearException):
    """The selected model/provider does not support the requested input type."""

    def __init__(self, provider: str, modality: str) -> None:
        super().__init__(
            f"Provider '{provider}' does not support {modality} input with the "
            "configured model. Use a multimodal model or extract text first.",
            status_code=422,
        )


class DocumentProcessingError(MediClearException):
    """Document could not be read or processed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=422)


class UnsupportedFileTypeError(MediClearException):
    """The uploaded file type is not accepted."""

    def __init__(self, content_type: str) -> None:
        super().__init__(
            f"File type '{content_type}' is not supported. "
            "Accepted types: PDF (application/pdf), JPEG, PNG.",
            status_code=415,
        )


class FileTooLargeError(MediClearException):
    """The uploaded file exceeds the configured size limit."""

    def __init__(self, max_mb: int) -> None:
        super().__init__(
            f"File exceeds the maximum allowed size of {max_mb} MB.",
            status_code=413,
        )


class SessionNotFoundError(MediClearException):
    """Chat session not found or has expired."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Chat session '{session_id}' was not found or has expired. "
            "Please analyse a document first to start a new session.",
            status_code=404,
        )


class TTSError(MediClearException):
    """Text-to-speech synthesis failed."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Text-to-speech failed: {message}", status_code=502)


class AuthenticationError(MediClearException):
    """Missing or invalid API key."""

    def __init__(self, message: str = "Missing or invalid API key.") -> None:
        super().__init__(message, status_code=401)


class RateLimitError(MediClearException):
    """The client exceeded its rate limit."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after} seconds.",
            status_code=429,
        )


class ChatDisabledError(MediClearException):
    """Follow-up chat is unavailable (e.g. zero-retention mode)."""

    def __init__(self) -> None:
        super().__init__(
            "Follow-up chat is disabled because the server runs in zero-retention "
            "mode. Re-submit the document to ask questions.",
            status_code=409,
        )


class FeatureDisabledError(MediClearException):
    """A requested feature is turned off by configuration."""

    def __init__(self, feature: str) -> None:
        super().__init__(f"The '{feature}' feature is disabled on this server.", status_code=404)
