from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(
        ...,
        description="Correo electrónico registrado del usuario",
        examples=["usuario@fhk.app"],
    )
    password: str = Field(
        ...,
        min_length=6,
        description="Contraseña del usuario",
        examples=["MiPasswordSeguro123!"],
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        description="Refresh token obtenido durante el login para renovar el access token",
    )


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Access Token para enviar en Authorization: Bearer <token>")
    refresh_token: str = Field(..., description="JWT Refresh Token para renovar sesión sin pedir contraseña")
    token_type: str = Field(default="bearer", description="Tipo de token de autorización")
    expires_in_minutes: int = Field(..., description="Tiempo de expiración del access token en minutos")
