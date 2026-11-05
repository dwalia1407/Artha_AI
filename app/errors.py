"""
Typed application errors.

The same error classes are used by web pages, the JSON API and the future
read-only agent tool boundary, so each failure has one stable code.
"""


class AppError(Exception):
    status = 400
    code = "invalid_request"

    def __init__(self, message="", details=None, status=None, code=None):
        super().__init__(message or self.code)
        self.message = message or self.code
        self.details = details or {}
        if status is not None:
            self.status = status
        if code is not None:
            self.code = code


class InvalidRequest(AppError):
    status = 400
    code = "invalid_request"


class Unauthenticated(AppError):
    status = 401
    code = "unauthenticated"


class Unauthorized(AppError):
    """Authenticated, but not allowed (for example a viewer trying to write)."""
    status = 403
    code = "unauthorized"


class NotFound(AppError):
    """Also used when a resource exists in a household the actor cannot see."""
    status = 404
    code = "not_found"


class Conflict(AppError):
    status = 409
    code = "conflict"


class MissingData(AppError):
    status = 404
    code = "missing_data"


class ServiceUnavailable(AppError):
    status = 503
    code = "service_unavailable"


class EmailNotVerified(Unauthorized):
    code = "email_not_verified"


class RateLimited(AppError):
    status = 429
    code = "rate_limited"

    def __init__(self, message="Too many attempts. Please try again later.", retry_after=None, details=None):
        det = dict(details or {})
        if retry_after is not None:
            det["retry_after"] = int(retry_after)
        super().__init__(message=message, details=det)
        self.retry_after = retry_after
