from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    # Authentication & Security
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    INVALID_OR_EXPIRED_TOKEN = "INVALID_OR_EXPIRED_TOKEN"
    INVALID_REFRESH_TOKEN = "INVALID_REFRESH_TOKEN"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    RECOVERY_CODE_NOT_REQUESTED = "RECOVERY_CODE_NOT_REQUESTED"
    RECOVERY_CODE_EXPIRED = "RECOVERY_CODE_EXPIRED"
    INVALID_RECOVERY_CODE = "INVALID_RECOVERY_CODE"

    # Family Ownership & Authorization
    PARENT_EMAIL_NOT_FOUND = "PARENT_EMAIL_NOT_FOUND"
    PARENT_EMAIL_MISMATCH = "PARENT_EMAIL_MISMATCH"

    # Family Members
    FAMILY_MEMBER_ALREADY_EXISTS = "FAMILY_MEMBER_ALREADY_EXISTS"
    FAMILY_MEMBER_NOT_FOUND = "FAMILY_MEMBER_NOT_FOUND"

    # Tasks
    TASK_NOT_FOUND = "TASK_NOT_FOUND"

    # Goals & Member Goals
    GOAL_NOT_FOUND = "GOAL_NOT_FOUND"
    MEMBER_GOAL_NOT_FOUND = "MEMBER_GOAL_NOT_FOUND"

    # Rewards & Member Rewards
    REWARD_NOT_FOUND = "REWARD_NOT_FOUND"
    MEMBER_REWARD_NOT_FOUND = "MEMBER_REWARD_NOT_FOUND"
    REWARD_NAME_OR_ID_REQUIRED = "REWARD_NAME_OR_ID_REQUIRED"

    # Member Balances
    MEMBER_BALANCE_NOT_FOUND = "MEMBER_BALANCE_NOT_FOUND"

    # Generic / Validation / System
    VALIDATION_ERROR = "VALIDATION_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


# Metadata mapping (HTTP Status Code, Default Detail Message) for every controlled error code
ERROR_CATALOG: Dict[ErrorCode, Tuple[int, str]] = {
    ErrorCode.INVALID_CREDENTIALS: (
        status.HTTP_401_UNAUTHORIZED,
        "Incorrect parent email or password.",
    ),
    ErrorCode.INVALID_OR_EXPIRED_TOKEN: (
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials or the access token has expired.",
    ),
    ErrorCode.INVALID_REFRESH_TOKEN: (
        status.HTTP_401_UNAUTHORIZED,
        "The provided refresh token is invalid or has expired.",
    ),
    ErrorCode.ACCOUNT_INACTIVE: (
        status.HTTP_403_FORBIDDEN,
        "The family account is currently inactive.",
    ),
    ErrorCode.EMAIL_ALREADY_REGISTERED: (
        status.HTTP_400_BAD_REQUEST,
        "A family account is already registered with this email_parent.",
    ),
    ErrorCode.USER_NOT_FOUND: (
        status.HTTP_404_NOT_FOUND,
        "No registered account was found with the provided email_parent.",
    ),
    ErrorCode.RECOVERY_CODE_NOT_REQUESTED: (
        status.HTTP_400_BAD_REQUEST,
        "No active password recovery request exists for this account.",
    ),
    ErrorCode.RECOVERY_CODE_EXPIRED: (
        status.HTTP_400_BAD_REQUEST,
        "The recovery code has expired. Please request a new one.",
    ),
    ErrorCode.INVALID_RECOVERY_CODE: (
        status.HTTP_400_BAD_REQUEST,
        "The 6-digit recovery code is incorrect.",
    ),
    ErrorCode.PARENT_EMAIL_NOT_FOUND: (
        status.HTTP_404_NOT_FOUND,
        "No registered family account was found with the provided parent email.",
    ),
    ErrorCode.PARENT_EMAIL_MISMATCH: (
        status.HTTP_403_FORBIDDEN,
        "The provided parent email does not match the authenticated JWT account.",
    ),
    ErrorCode.FAMILY_MEMBER_ALREADY_EXISTS: (
        status.HTTP_400_BAD_REQUEST,
        "A family member is already registered with this identification_uuid.",
    ),
    ErrorCode.FAMILY_MEMBER_NOT_FOUND: (
        status.HTTP_404_NOT_FOUND,
        "No family member was found with the provided UUID for this family.",
    ),
    ErrorCode.TASK_NOT_FOUND: (
        status.HTTP_404_NOT_FOUND,
        "No task was found with the provided task_id for this family.",
    ),
    ErrorCode.GOAL_NOT_FOUND: (
        status.HTTP_404_NOT_FOUND,
        "No parent goal was found with the provided goal_id for this family.",
    ),
    ErrorCode.MEMBER_GOAL_NOT_FOUND: (
        status.HTTP_404_NOT_FOUND,
        "No member goal was found with the provided member_goal_id for this family.",
    ),
    ErrorCode.REWARD_NOT_FOUND: (
        status.HTTP_404_NOT_FOUND,
        "No parent reward was found with the provided reward_id for this family.",
    ),
    ErrorCode.MEMBER_REWARD_NOT_FOUND: (
        status.HTTP_404_NOT_FOUND,
        "No claimed reward was found with the provided member_reward_id for this family.",
    ),
    ErrorCode.REWARD_NAME_OR_ID_REQUIRED: (
        status.HTTP_400_BAD_REQUEST,
        "You must provide either reward_id (to resolve the name automatically) or name_reward.",
    ),
    ErrorCode.MEMBER_BALANCE_NOT_FOUND: (
        status.HTTP_404_NOT_FOUND,
        "No balance record was found for the provided member_id.",
    ),
    ErrorCode.VALIDATION_ERROR: (
        422,
        "Request payload or parameter validation failed.",
    ),
    ErrorCode.HTTP_ERROR: (
        status.HTTP_400_BAD_REQUEST,
        "HTTP request error.",
    ),
    ErrorCode.INTERNAL_SERVER_ERROR: (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "An unexpected internal server error occurred.",
    ),
}


class AppHTTPException(HTTPException):
    """Structured HTTPException carrying a machine-readable `error_code`."""

    def __init__(
        self,
        error_code: ErrorCode,
        detail: Optional[str] = None,
        status_code: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        default_status, default_detail = ERROR_CATALOG[error_code]
        self.error_code = error_code
        super().__init__(
            status_code=status_code or default_status,
            detail=detail or default_detail,
            headers=headers,
        )


def api_error_responses(*error_codes: ErrorCode) -> Dict[int, Dict[str, Any]]:
    """Build clean OpenAPI/Swagger error response examples grouped by HTTP status code."""
    from app.schemas.error import ErrorResponse

    grouped: Dict[int, Dict[str, Any]] = {}
    for code in error_codes:
        http_status, default_detail = ERROR_CATALOG[code]
        if http_status not in grouped:
            grouped[http_status] = {
                "model": ErrorResponse,
                "description": f"Controlled error response(s) for HTTP {http_status}",
                "content": {"application/json": {"examples": {}}},
            }
        grouped[http_status]["content"]["application/json"]["examples"][code.value] = {
            "summary": code.value,
            "value": {
                "error_code": code.value,
                "detail": default_detail,
            },
        }
    return grouped
