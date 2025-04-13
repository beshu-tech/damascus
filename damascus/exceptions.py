"""
Exceptions for the Damascus SDK.
"""

from typing import Optional


class DamascusError(Exception):
    """Base exception for all Damascus SDK errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self) -> str:
        error_str = self.message
        if self.status_code:
            error_str += f" (Status: {self.status_code})"
        if self.error_code:
            error_str += f" (Error Code: {self.error_code})"
        return error_str


class AuthenticationError(DamascusError):
    """Raised when authentication fails."""

    pass


class ConfigurationError(DamascusError):
    """Raised when there is an issue with the client configuration."""

    pass


class ResourceNotFoundError(DamascusError):
    """Raised when a requested resource is not found."""

    pass


class ValidationError(DamascusError):
    """Raised when input validation fails."""

    pass


class RateLimitError(DamascusError):
    """Raised when API rate limits are exceeded."""

    pass


class ServerError(DamascusError):
    """Raised when the server returns a 5XX error."""

    pass
