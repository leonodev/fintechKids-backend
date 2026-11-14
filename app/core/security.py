from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any, Dict, Optional

import bcrypt
import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


def _normalize_password_bytes(raw_password: str) -> bytes:
    """Pre-hashea con SHA-256 para admitir cadenas encriptadas desde la app de cualquier longitud sin límite de 72 bytes de bcrypt."""
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest().encode("utf-8")


def verify_password(plain_or_client_encrypted_password: str, hashed_password: str) -> bool:
    """Verifica el password enviado desde la app contra el hash bcrypt almacenado en BD."""
    return bcrypt.checkpw(
        _normalize_password_bytes(plain_or_client_encrypted_password),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(plain_or_client_encrypted_password: str) -> str:
    """Genera un hash seguro usando bcrypt sobre el password encriptado recibido de la app."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(
        _normalize_password_bytes(plain_or_client_encrypted_password),
        salt,
    ).decode("utf-8")


def create_access_token(subject: str | int, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Genera un Access Token JWT de corta duración."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    """Genera un Refresh Token JWT de larga duración para renovar sesión desde la app."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decodifica y valida un token JWT (firma y expiración)."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware que añade cabeceras de seguridad estándar a todas las respuestas HTTP."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
