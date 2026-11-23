from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.errors import ErrorCode


class ErrorResponse(BaseModel):
    error_code: ErrorCode = Field(
        ...,
        description="Controlled machine-readable error code for client apps to localize and handle errors reliably",
        examples=["INVALID_RECOVERY_CODE"],
    )
    detail: str = Field(
        ...,
        description="Human-readable error message explaining what went wrong",
        examples=["The 6-digit recovery code is incorrect."],
    )
    errors: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional field-level validation details (present on HTTP 422 validation errors)",
    )
