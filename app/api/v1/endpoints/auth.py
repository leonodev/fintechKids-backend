from __future__ import annotations

from datetime import datetime, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

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
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nueva familia / padre",
    description=(
        "Registra una familia en la base de datos recibiendo `name_family`, `email_parent` y `approve_pin`. "
        "El campo `created_at` se asigna automáticamente en el servidor con la hora actual en UTC."
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
        approve_pin=user_in.approve_pin,
        hashed_pin=get_password_hash(user_in.approve_pin),
        is_active=True,
        role="parent",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión desde la App (JSON)",
    description="Recibe `email_parent` y `approve_pin` en formato JSON y devuelve un `access_token` y `refresh_token` JWT.",
)
def login_json(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email_parent == credentials.email_parent.lower()).first()
    if not user or not verify_password(credentials.approve_pin, user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo del padre (email_parent) o PIN (approve_pin) incorrectos.",
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
    "/token",
    response_model=TokenResponse,
    include_in_schema=False,
)
def login_oauth2_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Endpoint compatible con el formulario interactivo 'Authorize' de Swagger UI (username=email_parent, password=approve_pin)."""
    user = db.query(User).filter(User.email_parent == form_data.username.lower()).first()
    if not user or not verify_password(form_data.password, user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo del padre o PIN incorrectos.",
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
    summary="Renovar Access Token usando Refresh Token",
    description="Permite a la app móvil obtener un nuevo `access_token` sin obligar al usuario a iniciar sesión nuevamente.",
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
