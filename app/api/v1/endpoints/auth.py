from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.audit import record_activity
from app.core.config import settings
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
)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    existing_user = db.query(User).filter(User.email_parent == user_in.email_parent.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una familia registrada con este correo electrónico (email_parent).",
        )

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
)
def login_json(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email_parent == credentials.email_parent.lower()).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo del padre (email_parent) o contraseña (password) incorrectos.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta se encuentra desactivada.",
        )

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
)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    user = db.query(User).filter(User.email_parent == body.email_parent.lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe ninguna cuenta registrada con este correo electrónico (email_parent).",
        )

    recovery_code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_CODE_EXPIRE_MINUTES)

    user.reset_code = recovery_code
    user.reset_code_expires_at = expires_at
    user.updated_at = datetime.now(timezone.utc)

    db.add(user)
    db.commit()

    return ForgotPasswordResponse(
        message="Se ha generado y enviado un código de verificación de 6 dígitos al correo registrado.",
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
)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)) -> ResetPasswordResponse:
    user = db.query(User).filter(User.email_parent == body.email_parent.lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe ninguna cuenta registrada con este correo electrónico (email_parent).",
        )

    if not user.reset_code or not user.reset_code_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay una solicitud de recuperación de contraseña activa para esta cuenta.",
        )

    expires_at = user.reset_code_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        user.reset_code = None
        user.reset_code_expires_at = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de recuperación ha expirado. Solicita uno nuevo.",
        )

    if user.reset_code != body.recovery_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de recuperación de 6 dígitos es incorrecto.",
        )

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
        message="La contraseña se ha actualizado correctamente. Ya puedes iniciar sesión.",
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo del padre o contraseña incorrectos.",
        )
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
)
def refresh_access_token(body: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El token proporcionado no es un refresh token válido.",
            )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo.",
        )

    return TokenResponse(
        access_token=create_access_token(
            user.id,
            extra_claims={"email_parent": user.email_parent, "name_family": user.name_family, "role": user.role},
        ),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
