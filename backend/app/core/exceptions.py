from typing import Any, Dict, Optional

from fastapi import status


class VulnovaException(Exception):
    """Base Enterprise Exception for all Vulnova Backend Errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ResourceNotFoundException(VulnovaException):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Requested resource does not exist",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class UnauthorizedException(VulnovaException):
    """Exception raised when user authentication fails."""

    def __init__(
        self,
        message: str = "Authentication credentials were invalid or missing",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenException(VulnovaException):
    """Exception raised when user lacks authorization for a resource."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ValidationException(VulnovaException):
    """Exception raised when input data validation fails."""

    def __init__(
        self,
        message: str = "Request input data validation failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ConflictException(VulnovaException):
    """Exception raised when a resource conflict occurs (e.g. duplicate resource)."""

    def __init__(
        self,
        message: str = "Resource conflict occurred",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="RESOURCE_CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class LLMProviderException(VulnovaException):
    """Exception raised when LLM provider API communication fails or all fallbacks fail."""

    def __init__(
        self,
        message: str = "LLM provider execution failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="LLM_PROVIDER_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


class SecurityException(VulnovaException):
    """Exception raised during security or encryption operation failure."""

    def __init__(
        self,
        message: str = "Security operation failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="SECURITY_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )
