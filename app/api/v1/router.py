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
    auth.router,
    prefix="/auth",
    tags=["3. Authentication"],
)
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["4. Users / Family"],
)
api_router.include_router(
    family_members.router,
    prefix="/family-members",
    tags=["5. Family Members"],
)
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["6. Family Tasks"],
)
api_router.include_router(
    goals.router,
    prefix="/goals",
    tags=["7. Parent Goals"],
)
api_router.include_router(
    rewards.router,
    prefix="/rewards",
    tags=["8. Parent Rewards"],
)
api_router.include_router(
    member_goals.router,
    prefix="/member-goals",
    tags=["9. Member Goals"],
)
api_router.include_router(
    member_rewards.router,
    prefix="/member-rewards",
    tags=["10. Member Rewards"],
)
api_router.include_router(
    member_balances.router,
    prefix="/member-balances",
    tags=["11. Member Balances"],
)
api_router.include_router(
    activity_logs.router,
    prefix="/activity-logs",
    tags=["12. Activity History (Audit Logs)"],
)
api_router.include_router(
    remote_config.router,
    prefix="/remote-config",
    tags=["13. Remote Config"],
)
