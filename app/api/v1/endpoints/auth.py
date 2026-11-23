from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
import jwt
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.audit import record_activity
from app.core.config import settings
from app.core.errors import AppHTTPException, ErrorCode, api_error_responses
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
)
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new family / parent",
    description=(
        "Registers a family in the database receiving `name_family`, `email_parent`, "
        "`password` (client-encrypted from the app), and `approve_pin`. "
        "The `created_at` field is automatically assigned by the server in UTC."
    ),
    responses=api_error_responses(ErrorCode.EMAIL_ALREADY_REGISTERED),
)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    existing_user = db.query(User).filter(User.email_parent == user_in.email_parent.lower()).first()
    if existing_user:
        raise AppHTTPException(error_code=ErrorCode.EMAIL_ALREADY_REGISTERED)

    user = User(
        created_at=datetime.now(timezone.utc),
        name_family=user_in.name_family,
        email_parent=user_in.email_parent.lower(),
        hashed_password=get_password_hash(user_in.password),
        approve_pin=user_in.approve_pin,
        is_active=True,
        role="parent",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    record_activity(
        db,
        parent_id=user.id,
        email_parent=user.email_parent,
        action="REGISTER_FAMILY",
        entity_type="users",
        entity_id=user.id,
        details=f"Registro de familia '{user.name_family}'",
    )
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in from the App (JSON)",
    description=(
        "Receives `email_parent` and `password` (the same client-encrypted password sent during registration) "
        "and returns a JWT `access_token` and `refresh_token`."
    ),
    responses=api_error_responses(ErrorCode.INVALID_CREDENTIALS, ErrorCode.ACCOUNT_INACTIVE),
)
def login_json(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email_parent == credentials.email_parent.lower()).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise AppHTTPException(error_code=ErrorCode.INVALID_CREDENTIALS)
    if not user.is_active:
        raise AppHTTPException(error_code=ErrorCode.ACCOUNT_INACTIVE)

    return TokenResponse(
        access_token=create_access_token(
            user.id,
            extra_claims={"email_parent": user.email_parent, "name_family": user.name_family, "role": user.role},
        ),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Password Recovery - Step 1: Request 6-digit verification code",
    description=(
        "Receives `email_parent`, generates a temporary 6-digit recovery code valid for 15 minutes, "
        "and persists it in the database to be sent to the parent's email."
    ),
    responses=api_error_responses(ErrorCode.USER_NOT_FOUND),
)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    user = db.query(User).filter(User.email_parent == body.email_parent.lower()).first()
    if not user:
        raise AppHTTPException(error_code=ErrorCode.USER_NOT_FOUND)

    recovery_code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_CODE_EXPIRE_MINUTES)

    user.reset_code = recovery_code
    user.reset_code_expires_at = expires_at
    user.updated_at = datetime.now(timezone.utc)

    db.add(user)
    db.commit()

    return ForgotPasswordResponse(
        message="A 6-digit verification code has been generated and sent to the registered email.",
        email_parent=user.email_parent,
        expires_in_minutes=settings.RESET_CODE_EXPIRE_MINUTES,
        debug_recovery_code=(
            recovery_code
            if settings.ENVIRONMENT.lower() in {"development", "stage", "staging"}
            else None
        ),
    )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Password Recovery - Step 2: Confirm code and update password",
    description=(
        "Receives `email_parent`, `recovery_code` (6 digits), and the new client-encrypted `new_password`. "
        "Validates that the code matches and has not expired, updates the password in the database, and invalidates the code."
    ),
    responses=api_error_responses(
        ErrorCode.USER_NOT_FOUND,
        ErrorCode.RECOVERY_CODE_NOT_REQUESTED,
        ErrorCode.RECOVERY_CODE_EXPIRED,
        ErrorCode.INVALID_RECOVERY_CODE,
    ),
)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)) -> ResetPasswordResponse:
    user = db.query(User).filter(User.email_parent == body.email_parent.lower()).first()
    if not user:
        raise AppHTTPException(error_code=ErrorCode.USER_NOT_FOUND)

    if not user.reset_code or not user.reset_code_expires_at:
        raise AppHTTPException(error_code=ErrorCode.RECOVERY_CODE_NOT_REQUESTED)

    expires_at = user.reset_code_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        user.reset_code = None
        user.reset_code_expires_at = None
        db.commit()
        raise AppHTTPException(error_code=ErrorCode.RECOVERY_CODE_EXPIRED)

    if user.reset_code != body.recovery_code:
        raise AppHTTPException(error_code=ErrorCode.INVALID_RECOVERY_CODE)

    now_utc = datetime.now(timezone.utc)
    user.hashed_password = get_password_hash(body.new_password)
    user.reset_code = None
    user.reset_code_expires_at = None
    user.updated_at = now_utc

    db.add(user)
    db.commit()
    db.refresh(user)

    record_activity(
        db,
        parent_id=user.id,
        email_parent=user.email_parent,
        action="RESET_PASSWORD",
        entity_type="users",
        entity_id=user.id,
        details="Contraseña restablecida mediante código de verificación de 6 dígitos",
    )

    return ResetPasswordResponse(
        message="Password has been updated successfully. You can now log in.",
        email_parent=user.email_parent,
        updated_at=user.updated_at,
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    include_in_schema=False,
)
def login_oauth2_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Endpoint compatible con el formulario interactivo 'Authorize' de Swagger UI (username=email_parent, password=password)."""
    user = db.query(User).filter(User.email_parent == form_data.username.lower()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise AppHTTPException(error_code=ErrorCode.INVALID_CREDENTIALS)
    if not user.is_active:
        raise AppHTTPException(error_code=ErrorCode.ACCOUNT_INACTIVE)
    return TokenResponse(
        access_token=create_access_token(
            user.id,
            extra_claims={"email_parent": user.email_parent, "name_family": user.name_family, "role": user.role},
        ),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renew Access Token using Refresh Token",
    description="Allows the mobile app to obtain a new `access_token` without forcing the user to log in again.",
    responses=api_error_responses(ErrorCode.INVALID_REFRESH_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def refresh_access_token(body: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise AppHTTPException(error_code=ErrorCode.INVALID_REFRESH_TOKEN)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise AppHTTPException(error_code=ErrorCode.INVALID_REFRESH_TOKEN)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppHTTPException(error_code=ErrorCode.INVALID_REFRESH_TOKEN)
    if not user.is_active:
        raise AppHTTPException(error_code=ErrorCode.ACCOUNT_INACTIVE)

    return TokenResponse(
        access_token=create_access_token(
            user.id,
            extra_claims={"email_parent": user.email_parent, "name_family": user.name_family, "role": user.role},
        ),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
