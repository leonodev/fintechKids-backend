from __future__ import annotations

from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

# Permite autenticarse desde el botón "Authorize" de Swagger UI con email/password
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",
    scheme_name="OAuth2Password",
    auto_error=False,
)

# Permite pegar directamente un Bearer JWT token en Swagger UI o enviarlo desde la App
http_bearer = HTTPBearer(
    scheme_name="BearerJWT",
    description="Pega aquí tu `access_token` JWT obtenido en `/api/v1/auth/login`",
    auto_error=False,
)


def get_current_user(
    db: Session = Depends(get_db),
    oauth_token: Optional[str] = Depends(oauth2_scheme),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> User:
    """Valida el token JWT enviado en el header Authorization: Bearer <token>."""
    token = bearer_creds.credentials if bearer_creds else oauth_token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales o el token ha expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario se encuentra inactivo.",
        )
    return user
