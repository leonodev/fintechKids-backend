from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email_parent: EmailStr = Field(
        ...,
        description="Correo electrónico registrado del padre/tutor",
        examples=["padre@fhk.app"],
    )
    approve_pin: str = Field(
        ...,
        min_length=4,
        description="PIN de aprobación configurado en el registro",
        examples=["1234"],
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        description="Refresh token obtenido durante el login para renovar el access token",
    )


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Access Token para enviar en Authorization: Bearer <token>")
    refresh_token: str = Field(..., description="JWT Refresh Token para renovar sesión sin pedir PIN nuevamente")
    token_type: str = Field(default="bearer", description="Tipo de token de autorización")
    expires_in_minutes: int = Field(..., description="Tiempo de expiración del access token en minutos")
