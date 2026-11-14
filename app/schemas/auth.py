from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email_parent: EmailStr = Field(
        ...,
        description="Correo electrónico registrado del padre/tutor",
        examples=["padre@fhk.app"],
    )
    password: str = Field(
        ...,
        min_length=4,
        max_length=512,
        description="Contraseña encriptada desde la app (la misma enviada durante el registro)",
        examples=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        description="Refresh token obtenido durante el login para renovar el access token",
    )


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Access Token para enviar en Authorization: Bearer <token>")
    refresh_token: str = Field(..., description="JWT Refresh Token para renovar sesión sin pedir contraseña nuevamente")
    token_type: str = Field(default="bearer", description="Tipo de token de autorización")
    expires_in_minutes: int = Field(..., description="Tiempo de expiración del access token en minutos")
