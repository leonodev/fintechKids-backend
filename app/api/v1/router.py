from fastapi import APIRouter

from app.api.v1.endpoints import (
    activity_logs,
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

api_router.include_router(
    app_version.router,
    prefix="/app-version",
    tags=["2. Versión de la App (Tiendas)"],
)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["3. Autenticación"],
)
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["4. Usuarios / Familia"],
)
api_router.include_router(
    family_members.router,
    prefix="/family-members",
    tags=["5. Miembros de la Familia"],
)
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["6. Tareas de la Familia (Tasks)"],
)
api_router.include_router(
    goals.router,
    prefix="/goals",
    tags=["7. Metas del Padre (Goals)"],
)
api_router.include_router(
    rewards.router,
    prefix="/rewards",
    tags=["8. Recompensas del Padre (Rewards)"],
)
api_router.include_router(
    member_goals.router,
    prefix="/member-goals",
    tags=["9. Metas de los Miembros (Member Goals)"],
)
api_router.include_router(
    member_rewards.router,
    prefix="/member-rewards",
    tags=["10. Recompensas de los Miembros (Member Rewards)"],
)
api_router.include_router(
    member_balances.router,
    prefix="/member-balances",
    tags=["11. Balance de los Miembros (Member Balances)"],
)
api_router.include_router(
    activity_logs.router,
    prefix="/activity-logs",
    tags=["12. Historial de Actividad (Audit Logs)"],
)
