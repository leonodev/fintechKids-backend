from __future__ import annotations

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "FHK Backend API"
    PROJECT_DESCRIPTION: str = (
        "Backend REST API con autenticación JWT, seguridad, persistencia en base de datos "
        "y documentación interactiva OpenAPI/Swagger auto-generada."
    )
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Configuración JWT y Recuperación de Contraseña
    SECRET_KEY: str = "fhk-dev-secret-key-change-in-production-9f8e7d6c5b4a3f2e1d0c"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RESET_CODE_EXPIRE_MINUTES: int = 15

    # Base de datos (SQLite por defecto en local, PostgreSQL en producción)
    DATABASE_URL: str = "sqlite:///./fhk.db"

    # CORS
    BACKEND_CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> List[str]:
        if self.BACKEND_CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
