from __future__ import annotations

from datetime import datetime
from typing import Optional
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


class ForgotPasswordRequest(BaseModel):
    email_parent: EmailStr = Field(
        ...,
        description="Correo electrónico del padre/tutor para recibir el código temporal de 6 dígitos",
        examples=["padre@fhk.app"],
    )


class ForgotPasswordResponse(BaseModel):
    message: str = Field(
        ...,
        description="Mensaje de confirmación para mostrar al usuario en la app",
        examples=["Se ha generado y enviado un código de verificación de 6 dígitos al correo registrado."],
    )
    email_parent: EmailStr = Field(..., description="Correo al cual se envió el código")
    expires_in_minutes: int = Field(..., description="Minutos de validez del código de 6 dígitos")
    debug_recovery_code: Optional[str] = Field(
        default=None,
        description="Código de 6 dígitos expuesto únicamente en entorno `development` para facilitar pruebas desde la app o Swagger",
        examples=["482910"],
    )


class ResetPasswordRequest(BaseModel):
    email_parent: EmailStr = Field(
        ...,
        description="Correo electrónico del padre/tutor",
        examples=["padre@fhk.app"],
    )
    recovery_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="Código temporal de 6 dígitos recibido por correo",
        examples=["482910"],
    )
    new_password: str = Field(
        ...,
        min_length=4,
        max_length=512,
        description="Nueva contraseña encriptada desde la app",
        examples=["9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"],
    )


class ResetPasswordResponse(BaseModel):
    message: str = Field(
        ...,
        description="Confirmación del cambio de contraseña",
        examples=["La contraseña se ha actualizado correctamente. Ya puedes iniciar sesión."],
    )
    email_parent: EmailStr
    updated_at: datetime
