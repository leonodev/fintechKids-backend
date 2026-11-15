from fastapi import APIRouter

from app.api.v1.endpoints import (
    app_version,
    auth,
    family_members,
    goals,
    member_balances,
    member_goals,
    member_rewards,
    rewards,
    tasks,
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
    member_balances.router,
    prefix="/member-balances",
    tags=["6. Balance de los Miembros (Member Balances)"],
)
api_router.include_router(
    rewards.router,
    prefix="/rewards",
    tags=["7. Recompensas del Padre (Rewards)"],
)
api_router.include_router(
    member_rewards.router,
    prefix="/member-rewards",
    tags=["8. Recompensas de los Miembros (Member Rewards)"],
)
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["9. Tareas de la Familia (Tasks)"],
)
api_router.include_router(
    app_version.router,
    prefix="/app-version",
    tags=["10. Versión de la App (Tiendas)"],
)
