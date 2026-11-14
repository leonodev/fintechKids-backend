from fastapi import APIRouter

from app.api.v1.endpoints import (
    app_version,
    auth,
    family_members,
    goals,
    items,
    member_goals,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["1. Autenticación"])
api_router.include_router(users.router, prefix="/users", tags=["2. Usuarios / Familia"])
api_router.include_router(
    family_members.router,
    prefix="/family-members",
    tags=["3. Miembros de la Familia"],
)
api_router.include_router(
    goals.router,
    prefix="/goals",
    tags=["4. Metas del Padre (Goals)"],
)
api_router.include_router(
    member_goals.router,
    prefix="/member-goals",
    tags=["5. Metas de los Miembros (Member Goals)"],
)
api_router.include_router(
    app_version.router,
    prefix="/app-version",
    tags=["6. Versión de la App (Tiendas)"],
)
api_router.include_router(items.router, prefix="/items", tags=["7. Elementos (CRUD Ejemplo)"])
