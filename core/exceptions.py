"""Standardized exception handling for the application."""

from enum import Enum
from typing import Optional, Dict, Any


class ErrorCode(str, Enum):
    """Standardized error codes."""
    
    # Authentication errors (AUTH001-AUTH999)
    INVALID_CREDENTIALS = "AUTH001"
    TOKEN_EXPIRED = "AUTH002"
    INSUFFICIENT_PERMISSIONS = "AUTH003"
    ACCOUNT_NOT_FOUND = "AUTH004"
    ACCOUNT_ALREADY_EXISTS = "AUTH005"
    INVALID_AUTHENTICATION_FLOW = "AUTH006"
    OAUTH_CALLBACK_ERROR = "AUTH007"
    TOKEN_REFRESH_FAILED = "AUTH008"
    DEVICE_CODE_EXPIRED = "AUTH009"
    DEVICE_CODE_PENDING = "AUTH010"
    
    # Mail errors (MAIL001-MAIL999)
    MAIL_NOT_FOUND = "MAIL001"
    QUOTA_EXCEEDED = "MAIL002"
    INVALID_MAIL_QUERY = "MAIL003"
    MAIL_SEND_FAILED = "MAIL004"
    WEBHOOK_SUBSCRIPTION_FAILED = "MAIL005"
    DELTA_LINK_EXPIRED = "MAIL006"
    ATTACHMENT_TOO_LARGE = "MAIL007"
    INVALID_FOLDER_ID = "MAIL008"
    
    # External API errors (EXT001-EXT999)
    EXTERNAL_API_TIMEOUT = "EXT001"
    EXTERNAL_API_ERROR = "EXT002"
    EXTERNAL_API_UNAUTHORIZED = "EXT003"
    EXTERNAL_API_RATE_LIMITED = "EXT004"
    EXTERNAL_API_UNAVAILABLE = "EXT005"
    
    # Database errors (DB001-DB999)
    DATABASE_CONNECTION_ERROR = "DB001"
    DATABASE_CONSTRAINT_VIOLATION = "DB002"
    DATABASE_TRANSACTION_ERROR = "DB003"
    
    # Validation errors (VAL001-VAL999)
    INVALID_INPUT = "VAL001"
    MISSING_REQUIRED_FIELD = "VAL002"
    INVALID_EMAIL_FORMAT = "VAL003"
    INVALID_DATE_FORMAT = "VAL004"
    INVALID_UUID_FORMAT = "VAL005"
    
    # System errors (SYS001-SYS999)
    INTERNAL_SERVER_ERROR = "SYS001"
    SERVICE_UNAVAILABLE = "SYS002"
    CONFIGURATION_ERROR = "SYS003"
    RATE_LIMIT_EXCEEDED = "SYS004"


class BusinessException(Exception):
    """Base exception for business logic errors."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        result = {
            "error_code": self.error_code.value,
            "error_message": self.message,
            "details": self.details
        }
        
        if self.cause:
            result["cause"] = str(self.cause)
        
        return result


# Authentication Exceptions
class AuthenticationException(BusinessException):
    """Base authentication exception."""
    pass


class InvalidCredentialsException(AuthenticationException):
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            ErrorCode.INVALID_CREDENTIALS,
            "Invalid credentials provided",
            details
        )


class TokenExpiredException(AuthenticationException):
    def __init__(self, account_id: str):
        super().__init__(
            ErrorCode.TOKEN_EXPIRED,
            f"Token expired for account {account_id}",
            {"account_id": account_id}
        )


class AccountNotFoundException(AuthenticationException):
    def __init__(self, account_id: str):
        super().__init__(
            ErrorCode.ACCOUNT_NOT_FOUND,
            f"Account not found: {account_id}",
            {"account_id": account_id}
        )


class AccountAlreadyExistsException(AuthenticationException):
    def __init__(self, email: str):
        super().__init__(
            ErrorCode.ACCOUNT_ALREADY_EXISTS,
            f"Account already exists for email: {email}",
            {"email": email}
        )


class InsufficientPermissionsException(AuthenticationException):
    def __init__(self, required_scopes: list, current_scopes: list):
        super().__init__(
            ErrorCode.INSUFFICIENT_PERMISSIONS,
            "Insufficient permissions for this operation",
            {
                "required_scopes": required_scopes,
                "current_scopes": current_scopes
            }
        )


class DeviceCodeExpiredException(AuthenticationException):
    def __init__(self, device_code: str):
        super().__init__(
            ErrorCode.DEVICE_CODE_EXPIRED,
            "Device code has expired",
            {"device_code": device_code}
        )


class DeviceCodePendingException(AuthenticationException):
    def __init__(self, device_code: str):
        super().__init__(
            ErrorCode.DEVICE_CODE_PENDING,
            "Device code authorization is still pending",
            {"device_code": device_code}
        )


# Mail Exceptions
class MailException(BusinessException):
    """Base mail exception."""
    pass


class MailNotFoundException(MailException):
    def __init__(self, message_id: str):
        super().__init__(
            ErrorCode.MAIL_NOT_FOUND,
            f"Mail message not found: {message_id}",
            {"message_id": message_id}
        )


class QuotaExceededException(MailException):
    def __init__(self, quota_type: str, limit: int):
        super().__init__(
            ErrorCode.QUOTA_EXCEEDED,
            f"Quota exceeded for {quota_type}: {limit}",
            {"quota_type": quota_type, "limit": limit}
        )


class InvalidMailQueryException(MailException):
    def __init__(self, query_details: str):
        super().__init__(
            ErrorCode.INVALID_MAIL_QUERY,
            f"Invalid mail query: {query_details}",
            {"query_details": query_details}
        )


class MailSendFailedException(MailException):
    def __init__(self, recipient: str, reason: str):
        super().__init__(
            ErrorCode.MAIL_SEND_FAILED,
            f"Failed to send mail to {recipient}: {reason}",
            {"recipient": recipient, "reason": reason}
        )


class WebhookSubscriptionFailedException(MailException):
    def __init__(self, resource: str, reason: str):
        super().__init__(
            ErrorCode.WEBHOOK_SUBSCRIPTION_FAILED,
            f"Failed to create webhook subscription for {resource}: {reason}",
            {"resource": resource, "reason": reason}
        )


class DeltaLinkExpiredException(MailException):
    def __init__(self, account_id: str):
        super().__init__(
            ErrorCode.DELTA_LINK_EXPIRED,
            f"Delta link expired for account {account_id}",
            {"account_id": account_id}
        )


# External API Exceptions
class ExternalAPIException(BusinessException):
    """Base external API exception."""
    pass


class ExternalAPITimeoutException(ExternalAPIException):
    def __init__(self, endpoint: str, timeout: int):
        super().__init__(
            ErrorCode.EXTERNAL_API_TIMEOUT,
            f"External API timeout: {endpoint} (timeout: {timeout}s)",
            {"endpoint": endpoint, "timeout": timeout}
        )


class ExternalAPIErrorException(ExternalAPIException):
    def __init__(self, endpoint: str, status_code: int, response: str):
        super().__init__(
            ErrorCode.EXTERNAL_API_ERROR,
            f"External API error: {endpoint} returned {status_code}",
            {
                "endpoint": endpoint,
                "status_code": status_code,
                "response": response
            }
        )


class ExternalAPIRateLimitedException(ExternalAPIException):
    def __init__(self, endpoint: str, retry_after: Optional[int] = None):
        super().__init__(
            ErrorCode.EXTERNAL_API_RATE_LIMITED,
            f"External API rate limited: {endpoint}",
            {"endpoint": endpoint, "retry_after": retry_after}
        )


# Database Exceptions
class DatabaseException(BusinessException):
    """Base database exception."""
    pass


class DatabaseConnectionException(DatabaseException):
    def __init__(self, database_url: str, cause: Exception):
        super().__init__(
            ErrorCode.DATABASE_CONNECTION_ERROR,
            f"Failed to connect to database: {database_url}",
            {"database_url": database_url},
            cause
        )


class DatabaseConstraintViolationException(DatabaseException):
    def __init__(self, constraint: str, details: str):
        super().__init__(
            ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
            f"Database constraint violation: {constraint}",
            {"constraint": constraint, "details": details}
        )


# Validation Exceptions
class ValidationException(BusinessException):
    """Base validation exception."""
    pass


class InvalidInputException(ValidationException):
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            ErrorCode.INVALID_INPUT,
            f"Invalid input for field '{field}': {reason}",
            {"field": field, "value": str(value), "reason": reason}
        )


class MissingRequiredFieldException(ValidationException):
    def __init__(self, field: str):
        super().__init__(
            ErrorCode.MISSING_REQUIRED_FIELD,
            f"Missing required field: {field}",
            {"field": field}
        )


# System Exceptions
class SystemException(BusinessException):
    """Base system exception."""
    pass


class ConfigurationException(SystemException):
    def __init__(self, setting: str, reason: str):
        super().__init__(
            ErrorCode.CONFIGURATION_ERROR,
            f"Configuration error for '{setting}': {reason}",
            {"setting": setting, "reason": reason}
        )


class RateLimitExceededException(SystemException):
    def __init__(self, resource: str, limit: int, window: str):
        super().__init__(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            f"Rate limit exceeded for {resource}: {limit} requests per {window}",
            {"resource": resource, "limit": limit, "window": window}
        )


# Exception mapping for HTTP status codes
EXCEPTION_STATUS_CODE_MAP = {
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    ErrorCode.INSUFFICIENT_PERMISSIONS: 403,
    ErrorCode.ACCOUNT_NOT_FOUND: 404,
    ErrorCode.ACCOUNT_ALREADY_EXISTS: 409,
    ErrorCode.INVALID_AUTHENTICATION_FLOW: 400,
    ErrorCode.OAUTH_CALLBACK_ERROR: 400,
    ErrorCode.TOKEN_REFRESH_FAILED: 401,
    ErrorCode.DEVICE_CODE_EXPIRED: 400,
    ErrorCode.DEVICE_CODE_PENDING: 202,
    
    ErrorCode.MAIL_NOT_FOUND: 404,
    ErrorCode.QUOTA_EXCEEDED: 429,
    ErrorCode.INVALID_MAIL_QUERY: 400,
    ErrorCode.MAIL_SEND_FAILED: 500,
    ErrorCode.WEBHOOK_SUBSCRIPTION_FAILED: 500,
    ErrorCode.DELTA_LINK_EXPIRED: 410,
    ErrorCode.ATTACHMENT_TOO_LARGE: 413,
    ErrorCode.INVALID_FOLDER_ID: 400,
    
    ErrorCode.EXTERNAL_API_TIMEOUT: 504,
    ErrorCode.EXTERNAL_API_ERROR: 502,
    ErrorCode.EXTERNAL_API_UNAUTHORIZED: 502,
    ErrorCode.EXTERNAL_API_RATE_LIMITED: 429,
    ErrorCode.EXTERNAL_API_UNAVAILABLE: 503,
    
    ErrorCode.DATABASE_CONNECTION_ERROR: 503,
    ErrorCode.DATABASE_CONSTRAINT_VIOLATION: 409,
    ErrorCode.DATABASE_TRANSACTION_ERROR: 500,
    
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.MISSING_REQUIRED_FIELD: 400,
    ErrorCode.INVALID_EMAIL_FORMAT: 400,
    ErrorCode.INVALID_DATE_FORMAT: 400,
    ErrorCode.INVALID_UUID_FORMAT: 400,
    
    ErrorCode.INTERNAL_SERVER_ERROR: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.CONFIGURATION_ERROR: 500,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
}


def get_http_status_code(error_code: ErrorCode) -> int:
    """Get HTTP status code for error code."""
    return EXCEPTION_STATUS_CODE_MAP.get(error_code, 500)
