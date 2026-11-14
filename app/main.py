from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.security import SecurityHeadersMiddleware
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401 - Registra los modelos en el metadata de SQLAlchemy


openapi_tags = [
    {
        "name": "0. Estado del Servidor",
        "description": "Verificación de salud y disponibilidad del servicio.",
    },
    {
        "name": "1. Autenticación",
        "description": "Registro de usuarios, inicio de sesión y renovación de tokens JWT (`access_token` y `refresh_token`).",
    },
    {
        "name": "2. Usuarios / Familia",
        "description": "Consulta y actualización de los datos de la familia / padre autenticado.",
    },
    {
        "name": "3. Miembros de la Familia",
        "description": "Creación y consulta de miembros de la familia vinculados a la cuenta del padre.",
    },
    {
        "name": "4. Versión de la App (Tiendas)",
        "description": "Verificación de versión actual instalada en el dispositivo (`IOS` o `AND`) contra la última versión publicada en tiendas.",
    },
    {
        "name": "5. Elementos (CRUD Ejemplo)",
        "description": "Operaciones CRUD protegidas con JWT y persistidas en base de datos. Plantilla base para tus nuevos módulos.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea las tablas automáticamente al iniciar si no existen
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)

# Cabeceras de seguridad HTTP
app.add_middleware(SecurityHeadersMiddleware)

# Configuración CORS para consumo desde clientes Web / Móviles
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    tags=["0. Estado del Servidor"],
    summary="Health Check del Backend",
    description="Verifica que el servidor esté activo y listo para recibir peticiones.",
)
def health_check() -> dict:
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs",
        "openapi_url": f"{settings.API_V1_STR}/openapi.json",
    }


app.include_router(api_router, prefix=settings.API_V1_STR)
