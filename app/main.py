from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.security import SecurityHeadersMiddleware
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401


openapi_tags = [
    {
        "name": "1. Server Status",
        "description": "Service health check and availability status.",
    },
    {
        "name": "2. App Version (Stores)",
        "description": "Check the currently installed app version (`IOS` or `AND`) against the latest version published in stores.",
    },
    {
        "name": "3. Authentication",
        "description": "Family registration, login, 6-digit password recovery, and JWT token refresh (`access_token` and `refresh_token`).",
    },
    {
        "name": "4. Users / Family",
        "description": "Retrieve and update the authenticated parent / family profile.",
    },
    {
        "name": "5. Family Members",
        "description": "Create, update, list, and delete family members linked to the parent account.",
    },
    {
        "name": "6. Family Tasks",
        "description": "Create, edit, list (all or `enable` only), and delete family tasks created by the parent.",
    },
    {
        "name": "7. Parent Goals",
        "description": "Create and manage base goals configured by the family parent/guardian.",
    },
    {
        "name": "8. Parent Rewards",
        "description": "Create and manage rewards configured by the family parent/guardian.",
    },
    {
        "name": "9. Member Goals",
        "description": "Assign, list, update progress (`accumulated_value`), and delete goals selected by family members.",
    },
    {
        "name": "10. Member Rewards",
        "description": "Claim rewards (`PENDING`), update delivery state (`COLLECTED`), and delete claimed member rewards.",
    },
    {
        "name": "11. Member Balances",
        "description": "Create, retrieve, and update the coin (`coins_obtained`) and time (`time_obtained`) balance of each family member.",
    },
    {
        "name": "12. Activity History (Audit Logs)",
        "description": "Query the automated historical activity and audit trail recorded per family.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    tags=["1. Server Status"],
    summary="Backend Health Check",
    description="Verifies that the server is active and ready to accept requests.",
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

POSTMAN_DIR = Path(__file__).resolve().parent.parent / "postman"


@app.get("/postman/collection.json", include_in_schema=False)
def download_postman_collection() -> FileResponse:
    return FileResponse(
        path=POSTMAN_DIR / "FHKBackend.postman_collection.json",
        media_type="application/json",
        filename="FHKBackend.postman_collection.json",
    )


@app.get("/postman/environment.json", include_in_schema=False)
def download_postman_environment() -> FileResponse:
    return FileResponse(
        path=POSTMAN_DIR / "FHKBackend.postman_environment.json",
        media_type="application/json",
        filename="FHKBackend.postman_environment.json",
    )
