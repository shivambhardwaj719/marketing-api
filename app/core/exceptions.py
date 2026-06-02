from __future__ import annotations

from typing import Any


class AppException(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class AuthenticationError(AppException):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"
    message = "Authentication failed"


class TokenExpiredError(AppException):
    status_code = 401
    error_code = "TOKEN_EXPIRED"
    message = "Token has expired"


class PermissionDeniedError(AppException):
    status_code = 403
    error_code = "PERMISSION_DENIED"
    message = "Permission denied"


class NotFoundError(AppException):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class ConflictError(AppException):
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource already exists"


class ValidationError(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"


class RateLimitError(AppException):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests"


class FacebookAPIError(AppException):
    status_code = 502
    error_code = "FACEBOOK_API_ERROR"
    message = "Facebook API request failed"


class FacebookAuthError(AppException):
    status_code = 401
    error_code = "FACEBOOK_AUTH_ERROR"
    message = "Facebook authentication failed"


class WebhookVerificationError(AppException):
    status_code = 403
    error_code = "WEBHOOK_VERIFICATION_FAILED"
    message = "Webhook verification failed"


class ServiceUnavailableError(AppException):
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"
    message = "Service temporarily unavailable"
