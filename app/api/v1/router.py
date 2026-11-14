from fastapi import APIRouter

from app.api.v1.endpoints import app_version, auth, family_members, items, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["1. Autenticación"])
api_router.include_router(users.router, prefix="/users", tags=["2. Usuarios / Familia"])
api_router.include_router(
    family_members.router,
    prefix="/family-members",
    tags=["3. Miembros de la Familia"],
)
api_router.include_router(
    app_version.router,
    prefix="/app-version",
    tags=["4. Versión de la App (Tiendas)"],
)
api_router.include_router(items.router, prefix="/items", tags=["5. Elementos (CRUD Ejemplo)"])
