from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import AppHTTPException, ErrorCode
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
    {
        "name": "13. Remote Config",
        "description": "Retrieve and update global remote app configuration (cache TTL, enabled languages, and bottom-bar menu flags).",
    },
]


openapi_servers = [
    {
        "url": "/",
        "description": "Current Active Environment Server",
    },
    {
        "url": "https://fintechkids-backend-dev.onrender.com",
        "description": "Development Cloud (Render + Neon 'development' DB branch)",
    },
    {
        "url": "https://fintechkids-backend-stage.onrender.com",
        "description": "Stage / QA Cloud (Render + Neon 'stage' DB branch)",
    },
    {
        "url": "https://fintechkids-backend.onrender.com",
        "description": "Production Cloud (Render + Neon 'production' DB branch)",
    },
    {
        "url": "http://localhost:8000",
        "description": "Local Development Server (SQLite)",
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
    servers=openapi_servers,
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


@app.exception_handler(AppHTTPException)
async def app_http_exception_handler(request: Request, exc: AppHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code.value,
            "detail": exc.detail,
        },
        headers=exc.headers,
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": ErrorCode.HTTP_ERROR.value,
            "detail": str(exc.detail),
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error_code": ErrorCode.VALIDATION_ERROR.value,
            "detail": "Request payload or parameter validation failed.",
            "errors": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": ErrorCode.INTERNAL_SERVER_ERROR.value,
            "detail": "An unexpected internal server error occurred.",
        },
    )


@app.get(
    f"{settings.API_V1_STR}/health",
    tags=["1. Server Status"],
    summary="Backend Health Check",
    description="Verifies that the server is active and ready to accept requests.",
)
@app.get("/health", include_in_schema=False)
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
MOCKOON_DIR = Path(__file__).resolve().parent.parent / "mockoon"


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


@app.get("/mockoon/environment.json", include_in_schema=False)
def download_mockoon_environment() -> FileResponse:
    return FileResponse(
        path=MOCKOON_DIR / "FHKBackend.mockoon.json",
        media_type="application/json",
        filename="FHKBackend.mockoon.json",
    )


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from app.schemas.error import ErrorResponse

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers,
    )

    schemas = openapi_schema.setdefault("components", {}).setdefault("schemas", {})
    schemas.pop("HTTPValidationError", None)
    schemas.pop("ValidationError", None)

    error_response_schema = ErrorResponse.model_json_schema(ref_template="#/components/schemas/{model}")
    defs = error_response_schema.pop("$defs", {})
    for def_name, def_schema in defs.items():
        schemas[def_name] = def_schema
    schemas["ErrorResponse"] = error_response_schema

    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            if "422" in responses:
                responses["422"] = {
                    "description": "Validation Error (VALIDATION_ERROR)",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                            "example": {
                                "error_code": "VALIDATION_ERROR",
                                "detail": "Request payload or parameter validation failed.",
                                "errors": [
                                    {
                                        "type": "missing",
                                        "loc": ["body", "field_name"],
                                        "msg": "Field required",
                                    }
                                ],
                            },
                        }
                    },
                }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
