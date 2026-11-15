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
        "name": "1. Estado del servidor",
        "description": "Verificación de salud y disponibilidad del servicio.",
    },
    {
        "name": "2. Versión de la App (Tiendas)",
        "description": "Verificación de versión actual instalada en el dispositivo (`IOS` o `AND`) contra la última versión publicada en tiendas.",
    },
    {
        "name": "3. Autenticación",
        "description": "Registro de usuarios, inicio de sesión, recuperación de contraseña y renovación de tokens JWT (`access_token` y `refresh_token`).",
    },
    {
        "name": "4. Usuarios / Familia",
        "description": "Consulta y actualización de los datos de la familia / padre autenticado.",
    },
    {
        "name": "5. Miembros de la Familia",
        "description": "Creación, edición, consulta y eliminación de miembros de la familia vinculados a la cuenta del padre.",
    },
    {
        "name": "6. Tareas de la Familia (Tasks)",
        "description": "Creación, edición, consulta (todas o solo `enable`) y eliminación de tareas familiares creadas por el padre.",
    },
    {
        "name": "7. Metas del Padre (Goals)",
        "description": "Creación y gestión de metas base configuradas por el padre/tutor de la familia.",
    },
    {
        "name": "8. Recompensas del Padre (Rewards)",
        "description": "Creación y gestión de recompensas (`rewards`) configuradas por el padre/tutor de la familia.",
    },
    {
        "name": "9. Metas de los Miembros (Member Goals)",
        "description": "Asignación y seguimiento de metas seleccionadas por cada miembro de la familia.",
    },
    {
        "name": "10. Recompensas de los Miembros (Member Rewards)",
        "description": "Registro, cambio de estado (`PENDING` -> `COLLECTED`) y eliminación de recompensas reclamadas por los miembros.",
    },
    {
        "name": "11. Balance de los Miembros (Member Balances)",
        "description": "Registro y consulta de monedas (`coins_obtained`) y tiempo (`time_obtained`) de cada miembro.",
    },
    {
        "name": "12. Historial de Actividad (Audit Logs)",
        "description": "Consulta de la bitácora histórica de actividad y auditoría registrada automáticamente por familia.",
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
    tags=["1. Estado del servidor"],
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
