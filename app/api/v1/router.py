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
    remote_config,
    rewards,
    tasks,
    users,
)

api_router = APIRouter()

api_router.include_router(
    app_version.router,
    prefix="/app-version",
    tags=["2. App Version (Stores)"],
)
api_router.include_router(
    remote_config.router,
    prefix="/remote-config",
    tags=["3. Remote Config"],
)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["4. Authentication"],
)
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["5. Users / Family"],
)
api_router.include_router(
    family_members.router,
    prefix="/family-members",
    tags=["6. Family Members"],
)
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["7. Family Tasks"],
)
api_router.include_router(
    goals.router,
    prefix="/goals",
    tags=["8. Parent Goals"],
)
api_router.include_router(
    rewards.router,
    prefix="/rewards",
    tags=["9. Parent Rewards"],
)
api_router.include_router(
    member_goals.router,
    prefix="/member-goals",
    tags=["10. Member Goals"],
)
api_router.include_router(
    member_rewards.router,
    prefix="/member-rewards",
    tags=["11. Member Rewards"],
)
api_router.include_router(
    member_balances.router,
    prefix="/member-balances",
    tags=["12. Member Balances"],
)
api_router.include_router(
    activity_logs.router,
    prefix="/activity-logs",
    tags=["13. Activity History (Audit Logs)"],
)
