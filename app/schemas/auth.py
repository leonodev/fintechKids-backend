from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email_parent: EmailStr = Field(
        ...,
        description="Registered parent/guardian email address",
        examples=["parent@fhk.app"],
    )
    password: str = Field(
        ...,
        min_length=4,
        max_length=512,
        description="Client-encrypted password from the app (same value sent during registration)",
        examples=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        description="Refresh token obtained during login to renew the access token",
    )


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Access Token to send in `Authorization: Bearer <token>`")
    refresh_token: str = Field(..., description="JWT Refresh Token to renew the session without re-entering credentials")
    token_type: str = Field(default="bearer", description="Authorization token type")
    expires_in_minutes: int = Field(..., description="Access token expiration time in minutes")


class ForgotPasswordRequest(BaseModel):
    email_parent: EmailStr = Field(
        ...,
        description="Parent/guardian email address to receive the temporary 6-digit recovery code",
        examples=["parent@fhk.app"],
    )


class ForgotPasswordResponse(BaseModel):
    message: str = Field(
        ...,
        description="Confirmation message to display in the app",
        examples=["A 6-digit verification code has been generated and sent to the registered email."],
    )
    email_parent: EmailStr = Field(..., description="Email address where the recovery code was sent")
    expires_in_minutes: int = Field(..., description="Validity time in minutes for the 6-digit code")
    debug_recovery_code: Optional[str] = Field(
        default=None,
        description="6-digit code exposed only in the `development` environment to facilitate testing from the app or Swagger",
        examples=["482910"],
    )


class ResetPasswordRequest(BaseModel):
    email_parent: EmailStr = Field(
        ...,
        description="Registered parent/guardian email address",
        examples=["parent@fhk.app"],
    )
    recovery_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="Temporary 6-digit code received by email",
        examples=["482910"],
    )
    new_password: str = Field(
        ...,
        min_length=4,
        max_length=512,
        description="New client-encrypted password from the app",
        examples=["9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"],
    )


class ResetPasswordResponse(BaseModel):
    message: str = Field(
        ...,
        description="Password update confirmation message",
        examples=["Password has been updated successfully. You can now log in."],
    )
    email_parent: EmailStr
    updated_at: datetime
