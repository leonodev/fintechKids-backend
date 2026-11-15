"""Generate ready-to-import Postman Collection (v2.1) and Environment for FHKBackend.

Usage:
    python3 scripts/generate_postman.py
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.security import (  # noqa: E402
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402, F401
from app.models.app_version import AppVersion  # noqa: E402
from app.models.family_member import FamilyMember  # noqa: E402
from app.models.goal import Goal  # noqa: E402
from app.models.member_balance import MemberBalance  # noqa: E402
from app.models.member_goal import MemberGoal  # noqa: E402
from app.models.member_reward import MemberReward  # noqa: E402
from app.models.reward import Reward  # noqa: E402
from app.models.task import Task  # noqa: E402
from app.models.user import User  # noqa: E402


DEFAULT_EMAIL = "parent@fhk.app"
DEFAULT_PASSWORD = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
DEFAULT_FAMILY_NAME = "Leon Family"
DEFAULT_APPROVE_PIN = "1234"
DEFAULT_MEMBER_UUID = "550e8400-e29b-41d4-a716-446655440000"


def seed_demo_data() -> Dict[str, Any]:
    """Ensure local SQLite DB has default demo records so every Postman request works immediately."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. App Versions (IOS & AND)
        for platform, store_url in [
            ("IOS", "https://apps.apple.com/app/id000000000"),
            ("AND", "https://play.google.com/store/apps/details?id=com.fhk.app"),
        ]:
            existing_ver = db.query(AppVersion).filter(AppVersion.platform == platform).first()
            if not existing_ver:
                db.add(
                    AppVersion(
                        platform=platform,
                        latest_version="1.2.0",
                        min_required_version="1.0.0",
                        force_update=False,
                        store_url=store_url,
                        release_notes="Initial store configuration for FintechKids.",
                    )
                )

        # 2. Default Parent User
        user = db.query(User).filter(User.email_parent == DEFAULT_EMAIL).first()
        if not user:
            now = datetime.now(timezone.utc)
            user = User(
                created_at=now,
                updated_at=now,
                name_family=DEFAULT_FAMILY_NAME,
                email_parent=DEFAULT_EMAIL,
                hashed_password=get_password_hash(DEFAULT_PASSWORD),
                approve_pin=DEFAULT_APPROVE_PIN,
                is_active=True,
                role="user",
            )
            db.add(user)
            db.flush()

        # 3. Default Family Member
        member = (
            db.query(FamilyMember)
            .filter(FamilyMember.identification_uuid == DEFAULT_MEMBER_UUID)
            .first()
        )
        if not member:
            member = FamilyMember(
                identification_uuid=DEFAULT_MEMBER_UUID,
                email_parent=user.email_parent,
                name_family=user.name_family,
                member_name="Mateo",
                avatar_name="avatar_lion_01",
                parent_id=user.id,
            )
            db.add(member)
            db.flush()

        # 4. Default Task
        task = db.query(Task).filter(Task.parent_id == user.id).first()
        if not task:
            task = Task(
                name="Clean the bedroom",
                time_granted="00:30:00",
                coins_granted=50,
                email_parent=user.email_parent,
                description="Make the bed and put away all toys before dinner.",
                status="enable",
                parent_id=user.id,
            )
            db.add(task)
            db.flush()

        # 5. Default Goal
        goal = db.query(Goal).filter(Goal.parent_id == user.id).first()
        if not goal:
            goal = Goal(
                measure_type="minutes",
                status="active",
                email_parent=user.email_parent,
                name="Daily reading",
                value=30,
                parent_id=user.id,
            )
            db.add(goal)
            db.flush()

        # 6. Default Reward
        reward = db.query(Reward).filter(Reward.parent_id == user.id).first()
        if not reward:
            reward = Reward(
                name="1 hour of video games",
                time_required="01:00:00",
                coins_required=100,
                email_parent=user.email_parent,
                parent_id=user.id,
            )
            db.add(reward)
            db.flush()

        # 7. Default Member Goal
        member_goal = db.query(MemberGoal).filter(MemberGoal.parent_id == user.id).first()
        if not member_goal:
            member_goal = MemberGoal(
                goal_id=goal.id,
                member_id=DEFAULT_MEMBER_UUID,
                rewards_system_type="stars",
                rewards_system_value=10,
                accumulated_value=5,
                parent_email=user.email_parent,
                name=goal.name,
                parent_id=user.id,
            )
            db.add(member_goal)
            db.flush()

        # 8. Default Member Reward
        member_reward = db.query(MemberReward).filter(MemberReward.parent_id == user.id).first()
        if not member_reward:
            member_reward = MemberReward(
                reward_id=reward.id,
                member_id=DEFAULT_MEMBER_UUID,
                parent_email=user.email_parent,
                name_reward=reward.name,
                claimed_value="100 coins",
                state="PENDING",
                parent_id=user.id,
            )
            db.add(member_reward)
            db.flush()

        # 9. Default Member Balance
        member_balance = (
            db.query(MemberBalance)
            .filter(MemberBalance.member_id == DEFAULT_MEMBER_UUID)
            .first()
        )
        if not member_balance:
            member_balance = MemberBalance(
                member_id=DEFAULT_MEMBER_UUID,
                coins_obtained=150,
                time_obtained="01:30:00",
                parent_id=user.id,
            )
            db.add(member_balance)
            db.flush()

        db.commit()

        # Generate long-lived access token (30 days) so imported collection works out of the box
        access_token = create_access_token(
            subject=user.id,
            extra_claims={
                "email": user.email_parent,
                "role": user.role,
                "exp": datetime.now(timezone.utc) + timedelta(days=30),
            },
        )
        refresh_token = create_refresh_token(subject=user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "task_id": str(task.id),
            "goal_id": str(goal.id),
            "reward_id": str(reward.id),
            "member_goal_id": str(member_goal.id),
            "member_reward_id": str(member_reward.id),
        }
    finally:
        db.close()


def make_url(
    raw_path: str,
    query: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    clean_path = raw_path.lstrip("/")
    path_parts = clean_path.split("/") if clean_path else []
    raw = "{{base_url}}/" + clean_path
    if query:
        qs = "&".join(f"{q['key']}={q['value']}" for q in query if not q.get("disabled"))
        if qs:
            raw = f"{raw}?{qs}"
    url_obj: Dict[str, Any] = {
        "raw": raw,
        "host": ["{{base_url}}"],
        "path": path_parts,
    }
    if query:
        url_obj["query"] = query
    return url_obj


def make_request_item(
    name: str,
    method: str,
    path: str,
    description: str,
    body: Optional[Dict[str, Any]] = None,
    query: Optional[List[Dict[str, str]]] = None,
    public: bool = False,
    test_script_lines: Optional[List[str]] = None,
) -> Dict[str, Any]:
    headers: List[Dict[str, str]] = [
        {"key": "Accept", "value": "application/json", "type": "text"},
    ]
    if body is not None:
        headers.append({"key": "Content-Type", "value": "application/json", "type": "text"})

    request_obj: Dict[str, Any] = {
        "method": method,
        "header": headers,
        "url": make_url(path, query=query),
        "description": description,
    }

    if public:
        request_obj["auth"] = {"type": "noauth"}

    if body is not None:
        request_obj["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2, ensure_ascii=False),
            "options": {"raw": {"language": "json"}},
        }

    item: Dict[str, Any] = {
        "name": name,
        "request": request_obj,
        "response": [],
    }

    if test_script_lines:
        item["event"] = [
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": test_script_lines,
                },
            }
        ]

    return item


def build_token_capture_script() -> List[str]:
    return [
        "if (pm.response.code === 200 || pm.response.code === 201) {",
        "    const data = pm.response.json();",
        "    if (data.access_token) {",
        "        pm.collectionVariables.set('access_token', data.access_token);",
        "        if (pm.environment.name) { pm.environment.set('access_token', data.access_token); }",
        "        console.log('Updated access_token automatically.');",
        "    }",
        "    if (data.refresh_token) {",
        "        pm.collectionVariables.set('refresh_token', data.refresh_token);",
        "        if (pm.environment.name) { pm.environment.set('refresh_token', data.refresh_token); }",
        "    }",
        "}",
        "pm.test('Status code is 200 or 201', function () {",
        "    pm.expect(pm.response.code).to.be.oneOf([200, 201]);",
        "});",
    ]


def build_id_capture_script(json_field: str, var_name: str) -> List[str]:
    return [
        "if (pm.response.code === 200 || pm.response.code === 201) {",
        "    const data = pm.response.json();",
        f"    if (data.{json_field} !== undefined && data.{json_field} !== null) {{",
        f"        pm.collectionVariables.set('{var_name}', String(data.{json_field}));",
        f"        if (pm.environment.name) {{ pm.environment.set('{var_name}', String(data.{json_field})); }}",
        f"        console.log('Saved {var_name} =', data.{json_field});",
        "    }",
        "}",
        "pm.test('Status code is successful', function () {",
        "    pm.expect(pm.response.code).to.be.oneOf([200, 201]);",
        "});",
    ]


def build_collection(seeded: Dict[str, Any]) -> Dict[str, Any]:
    folders: List[Dict[str, Any]] = [
        # 1. Server Status
        {
            "name": "1. Server Status",
            "description": "Endpoints to verify that the API service is online and responding properly.",
            "item": [
                make_request_item(
                    name="Health Check",
                    method="GET",
                    path="/api/v1/health",
                    description="Verifies that the FastAPI server is online and returns the active environment.",
                    public=True,
                ),
            ],
        },
        # 2. App Version (Stores)
        {
            "name": "2. App Version (Stores)",
            "description": "Endpoints for mobile clients (`IOS` and `AND`) to check whether a newer or mandatory update exists in the App Store or Google Play.",
            "item": [
                make_request_item(
                    name="Check App Version (iOS)",
                    method="GET",
                    path="/api/v1/app-version/check",
                    query=[
                        {"key": "platform", "value": "IOS", "description": "IOS or AND"},
                        {"key": "current_version", "value": "1.0.0", "description": "Currently installed version"},
                    ],
                    description="Checks if an iOS update or mandatory force_update is available in the App Store.",
                    public=True,
                ),
                make_request_item(
                    name="Check App Version (Android)",
                    method="GET",
                    path="/api/v1/app-version/check",
                    query=[
                        {"key": "platform", "value": "AND", "description": "IOS or AND"},
                        {"key": "current_version", "value": "1.0.0", "description": "Currently installed version"},
                    ],
                    description="Checks if an Android update or mandatory force_update is available in Google Play.",
                    public=True,
                ),
                make_request_item(
                    name="List All Store Version Configs",
                    method="GET",
                    path="/api/v1/app-version",
                    description="Lists the stored version configurations for iOS (`IOS`) and Android (`AND`).",
                    public=True,
                ),
                make_request_item(
                    name="Update Store Version Config (Protected)",
                    method="PUT",
                    path="/api/v1/app-version/IOS",
                    description="Updates the latest/minimum required store version for `IOS` or `AND`. Requires Bearer JWT.",
                    body={
                        "latest_version": "1.3.0",
                        "min_required_version": "1.0.0",
                        "force_update": False,
                        "store_url": "https://apps.apple.com/app/id000000000",
                        "release_notes": "Performance improvements and new rewards module.",
                    },
                ),
            ],
        },
        # 3. Authentication
        {
            "name": "3. Authentication",
            "description": "Family registration, login with client-encrypted password, token refresh, and 2-step password recovery with a 6-digit code. Automatically saves `access_token` and `refresh_token` into collection variables.",
            "item": [
                make_request_item(
                    name="Register Family Account",
                    method="POST",
                    path="/api/v1/auth/register",
                    description="Registers a new parent/family account and automatically stores the returned `access_token` and `refresh_token`.",
                    public=True,
                    body={
                        "name_family": "{{name_family}}",
                        "email_parent": "{{email_parent}}",
                        "password": "{{password}}",
                        "approve_pin": "{{approve_pin}}",
                    },
                    test_script_lines=build_token_capture_script(),
                ),
                make_request_item(
                    name="Login (Auto-Saves JWT Token)",
                    method="POST",
                    path="/api/v1/auth/login",
                    description="Authenticates with `email_parent` and `password` and automatically saves `access_token` and `refresh_token` to collection & environment variables.",
                    public=True,
                    body={
                        "email_parent": "{{email_parent}}",
                        "password": "{{password}}",
                    },
                    test_script_lines=build_token_capture_script(),
                ),
                make_request_item(
                    name="Forgot Password (Request 6-Digit Code)",
                    method="POST",
                    path="/api/v1/auth/forgot-password",
                    description="Generates a 6-digit recovery code valid for 15 minutes and auto-saves `debug_recovery_code` into `{{reset_code}}`.",
                    public=True,
                    body={
                        "email_parent": "{{email_parent}}",
                    },
                    test_script_lines=build_id_capture_script("debug_recovery_code", "reset_code"),
                ),
                make_request_item(
                    name="Reset Password with 6-Digit Code",
                    method="POST",
                    path="/api/v1/auth/reset-password",
                    description="Validates the 6-digit `recovery_code` and updates the parent's encrypted password.",
                    public=True,
                    body={
                        "email_parent": "{{email_parent}}",
                        "recovery_code": "{{reset_code}}",
                        "new_password": "{{password}}",
                    },
                ),
                make_request_item(
                    name="Refresh Access Token",
                    method="POST",
                    path="/api/v1/auth/refresh",
                    description="Exchanges a valid `refresh_token` for a new pair of JWT tokens and auto-updates `{{access_token}}`.",
                    public=True,
                    body={
                        "refresh_token": "{{refresh_token}}",
                    },
                    test_script_lines=build_token_capture_script(),
                ),
            ],
        },
        # 4. Users / Family
        {
            "name": "4. Users / Family",
            "description": "Retrieve and update the authenticated parent/family profile (`/api/v1/users/me`).",
            "item": [
                make_request_item(
                    name="Get Current Family Profile (/me)",
                    method="GET",
                    path="/api/v1/users/me",
                    description="Returns the profile data of the currently authenticated parent/family.",
                ),
                make_request_item(
                    name="Update Current Family Profile (/me)",
                    method="PATCH",
                    path="/api/v1/users/me",
                    description="Updates `name_family`, `approve_pin`, or `password` for the authenticated parent account.",
                    body={
                        "name_family": "Leon Family",
                        "approve_pin": "1234",
                    },
                ),
            ],
        },
        # 5. Family Members
        {
            "name": "5. Family Members",
            "description": "Create, list, edit, and delete family members linked to the authenticated parent.",
            "item": [
                make_request_item(
                    name="Create Family Member",
                    method="POST",
                    path="/api/v1/family-members",
                    description="Registers a new family member and automatically saves `identification_uuid` into `{{member_id}}`.",
                    body={
                        "email_parent": "{{email_parent}}",
                        "identification_uuid": "550e8400-e29b-41d4-a716-446655440001",
                        "member_name": "Sofia",
                        "avatar_name": "avatar_unicorn_01",
                        "name_family": "{{name_family}}",
                    },
                    test_script_lines=build_id_capture_script("identification_uuid", "member_id"),
                ),
                make_request_item(
                    name="List All Family Members",
                    method="GET",
                    path="/api/v1/family-members",
                    description="Lists all family members belonging to the authenticated parent.",
                ),
                make_request_item(
                    name="Update Family Member by UUID",
                    method="PATCH",
                    path="/api/v1/family-members/{{member_id}}",
                    description="Partially updates `member_name` and/or `avatar_name` using `{{member_id}}`.",
                    body={
                        "member_name": "Mateo Updated",
                        "avatar_name": "avatar_tiger_02",
                    },
                ),
                make_request_item(
                    name="Delete Family Member by UUID",
                    method="DELETE",
                    path="/api/v1/family-members/{{member_id}}",
                    description="Deletes the family member identified by `{{member_id}}`.",
                ),
            ],
        },
        # 6. Family Tasks
        {
            "name": "6. Family Tasks",
            "description": "Create, edit (`enable`/`disable`), list all, list enabled, and delete tasks for a family.",
            "item": [
                make_request_item(
                    name="Create Family Task",
                    method="POST",
                    path="/api/v1/tasks",
                    description="Creates a new family task (status defaults to `enable`) and saves its `id` into `{{task_id}}`.",
                    body={
                        "name": "Clean the bedroom",
                        "time_granted": "00:30:00",
                        "coins_granted": 50,
                        "email_parent": "{{email_parent}}",
                        "description": "Make the bed and put away all toys before dinner.",
                        "status": "enable",
                    },
                    test_script_lines=build_id_capture_script("id", "task_id"),
                ),
                make_request_item(
                    name="Update Family Task (Edit or Enable/Disable)",
                    method="PATCH",
                    path="/api/v1/tasks/{{task_id}}",
                    description="Updates any field of the task including `status` (`enable` or `disable`).",
                    body={
                        "name": "Clean bedroom and desk",
                        "time_granted": "00:45:00",
                        "coins_granted": 75,
                        "description": "Make the bed, put away toys, and organize the desk.",
                        "status": "enable",
                    },
                ),
                make_request_item(
                    name="List All Family Tasks (Any Status)",
                    method="GET",
                    path="/api/v1/tasks",
                    description="Returns all tasks for the authenticated parent's family regardless of status (`enable` or `disable`).",
                ),
                make_request_item(
                    name="List Only Enabled Family Tasks",
                    method="GET",
                    path="/api/v1/tasks/enabled",
                    description="Returns only tasks with `status = enable` for the authenticated parent's family.",
                ),
                make_request_item(
                    name="Delete Family Task",
                    method="DELETE",
                    path="/api/v1/tasks/{{task_id}}",
                    description="Permanently deletes the task identified by `{{task_id}}`.",
                ),
            ],
        },
        # 7. Parent Goals
        {
            "name": "7. Parent Goals",
            "description": "Create, list, edit, and delete base goals configured by the parent.",
            "item": [
                make_request_item(
                    name="Create Parent Goal",
                    method="POST",
                    path="/api/v1/goals",
                    description="Creates a new parent goal and saves its `id` into `{{goal_id}}`.",
                    body={
                        "measure_type": "minutes",
                        "status": "active",
                        "email_parent": "{{email_parent}}",
                        "name": "Daily reading",
                        "value": 30,
                    },
                    test_script_lines=build_id_capture_script("id", "goal_id"),
                ),
                make_request_item(
                    name="List Parent Goals",
                    method="GET",
                    path="/api/v1/goals",
                    description="Lists all goals created by the authenticated parent.",
                ),
                make_request_item(
                    name="Update Parent Goal",
                    method="PATCH",
                    path="/api/v1/goals/{{goal_id}}",
                    description="Updates `name`, `measure_type`, `value`, or `status` (`active`/`inactive`) of a parent goal.",
                    body={
                        "name": "Evening reading",
                        "measure_type": "minutes",
                        "value": 45,
                        "status": "active",
                    },
                ),
                make_request_item(
                    name="Delete Parent Goal",
                    method="DELETE",
                    path="/api/v1/goals/{{goal_id}}",
                    description="Deletes the parent goal identified by `{{goal_id}}`.",
                ),
            ],
        },
        # 8. Parent Rewards
        {
            "name": "8. Parent Rewards",
            "description": "Create, list, edit, and delete rewards configured by the parent.",
            "item": [
                make_request_item(
                    name="Create Parent Reward",
                    method="POST",
                    path="/api/v1/rewards",
                    description="Creates a new parent reward and saves its `id` into `{{reward_id}}`.",
                    body={
                        "name": "1 hour of video games",
                        "time_required": "01:00:00",
                        "coins_required": 100,
                        "email_parent": "{{email_parent}}",
                    },
                    test_script_lines=build_id_capture_script("id", "reward_id"),
                ),
                make_request_item(
                    name="List Parent Rewards",
                    method="GET",
                    path="/api/v1/rewards",
                    description="Lists all rewards created by the authenticated parent.",
                ),
                make_request_item(
                    name="Update Parent Reward",
                    method="PATCH",
                    path="/api/v1/rewards/{{reward_id}}",
                    description="Updates `name`, `time_required`, or `coins_required` for a parent reward.",
                    body={
                        "name": "2 hours of video games",
                        "time_required": "02:00:00",
                        "coins_required": 180,
                    },
                ),
                make_request_item(
                    name="Delete Parent Reward",
                    method="DELETE",
                    path="/api/v1/rewards/{{reward_id}}",
                    description="Deletes the parent reward identified by `{{reward_id}}`.",
                ),
            ],
        },
        # 9. Member Goals
        {
            "name": "9. Member Goals",
            "description": "Assign goals to specific family members, track accumulated progress, and delete member goals.",
            "item": [
                make_request_item(
                    name="Create Member Goal",
                    method="POST",
                    path="/api/v1/member-goals",
                    description="Assigns a parent goal (`{{goal_id}}`) to a family member (`{{member_id}}`) and saves its `id` into `{{member_goal_id}}`.",
                    body={
                        "goal_id": 1,
                        "member_id": "{{member_id}}",
                        "rewards_system_type": "stars",
                        "rewards_system_value": 10,
                        "accumulated_value": 0,
                        "parent_email": "{{email_parent}}",
                        "name": "Daily reading",
                    },
                    test_script_lines=build_id_capture_script("id", "member_goal_id"),
                ),
                make_request_item(
                    name="List Member Goals",
                    method="GET",
                    path="/api/v1/member-goals",
                    query=[
                        {
                            "key": "member_id",
                            "value": "{{member_id}}",
                            "description": "Optional filter by family member UUID",
                            "disabled": True,
                        }
                    ],
                    description="Lists all member goals for the family (enable `member_id` query param to filter by a single child).",
                ),
                make_request_item(
                    name="Update Member Goal Progress",
                    method="PATCH",
                    path="/api/v1/member-goals/{{member_goal_id}}",
                    description="Updates `accumulated_value` or reward settings for a member's goal.",
                    body={
                        "accumulated_value": 15,
                        "rewards_system_type": "stars",
                        "rewards_system_value": 10,
                        "name": "Daily reading",
                    },
                ),
                make_request_item(
                    name="Delete Member Goal",
                    method="DELETE",
                    path="/api/v1/member-goals/{{member_goal_id}}",
                    description="Deletes the member goal identified by `{{member_goal_id}}`.",
                ),
            ],
        },
        # 10. Member Rewards
        {
            "name": "10. Member Rewards",
            "description": "Register rewards claimed by a family member (`PENDING`), mark them as delivered (`COLLECTED`), and delete claimed rewards.",
            "item": [
                make_request_item(
                    name="Claim Member Reward (State: PENDING)",
                    method="POST",
                    path="/api/v1/member-rewards",
                    description="Creates a claimed reward record in `PENDING` state and saves its `id` into `{{member_reward_id}}`.",
                    body={
                        "member_id": "{{member_id}}",
                        "parent_email": "{{email_parent}}",
                        "reward_id": 1,
                        "name_reward": "1 hour of video games",
                        "claimed_value": "100 coins",
                        "state": "PENDING",
                    },
                    test_script_lines=build_id_capture_script("id", "member_reward_id"),
                ),
                make_request_item(
                    name="List Claimed Member Rewards",
                    method="GET",
                    path="/api/v1/member-rewards",
                    query=[
                        {
                            "key": "member_id",
                            "value": "{{member_id}}",
                            "description": "Optional filter by member UUID",
                            "disabled": True,
                        },
                        {
                            "key": "state",
                            "value": "PENDING",
                            "description": "Optional filter by state (PENDING or COLLECTED)",
                            "disabled": True,
                        },
                    ],
                    description="Lists all claimed rewards for the family (optional filters: `member_id`, `state`).",
                ),
                make_request_item(
                    name="Update Claimed Reward State to COLLECTED",
                    method="PATCH",
                    path="/api/v1/member-rewards/{{member_reward_id}}",
                    description="Parent marks the claimed reward as `COLLECTED` once delivered to the family member.",
                    body={
                        "state": "COLLECTED",
                        "claimed_value": "100 coins",
                    },
                ),
                make_request_item(
                    name="Delete Claimed Member Reward",
                    method="DELETE",
                    path="/api/v1/member-rewards/{{member_reward_id}}",
                    description="Deletes the claimed reward identified by `{{member_reward_id}}`.",
                ),
            ],
        },
        # 11. Member Balances
        {
            "name": "11. Member Balances",
            "description": "Manage and query the accumulated coins and screen/play time balance for each family member.",
            "item": [
                make_request_item(
                    name="Create or Upsert Member Balance",
                    method="POST",
                    path="/api/v1/member-balances",
                    description="Creates or updates the balance (`coins_obtained` and `time_obtained`) for `{{member_id}}`.",
                    body={
                        "member_id": "{{member_id}}",
                        "coins_obtained": 150,
                        "time_obtained": "01:30:00",
                    },
                ),
                make_request_item(
                    name="List All Family Member Balances",
                    method="GET",
                    path="/api/v1/member-balances",
                    description="Lists the balances of all members in the authenticated family.",
                ),
                make_request_item(
                    name="Get Single Member Balance by UUID",
                    method="GET",
                    path="/api/v1/member-balances/{{member_id}}",
                    description="Retrieves the balance for a specific family member (`{{member_id}}`).",
                ),
                make_request_item(
                    name="Update Member Balance by UUID",
                    method="PATCH",
                    path="/api/v1/member-balances/{{member_id}}",
                    description="Partially updates `coins_obtained` and/or `time_obtained` for `{{member_id}}`.",
                    body={
                        "coins_obtained": 200,
                        "time_obtained": "02:00:00",
                    },
                ),
            ],
        },
        # 12. Activity History (Audit Logs)
        {
            "name": "12. Activity History (Audit Logs)",
            "description": "Read-only enterprise audit trail showing who performed what action and when across the family account.",
            "item": [
                make_request_item(
                    name="List Family Activity Logs",
                    method="GET",
                    path="/api/v1/activity-logs",
                    query=[
                        {"key": "limit", "value": "50", "description": "Max records to return (1-200)"},
                        {"key": "offset", "value": "0", "description": "Pagination offset"},
                        {
                            "key": "member_id",
                            "value": "{{member_id}}",
                            "description": "Optional filter by member UUID",
                            "disabled": True,
                        },
                        {
                            "key": "entity_type",
                            "value": "TASK",
                            "description": "Optional filter by entity type (USER, FAMILY_MEMBER, TASK, GOAL, REWARD, MEMBER_GOAL, MEMBER_REWARD, MEMBER_BALANCE)",
                            "disabled": True,
                        },
                        {
                            "key": "action",
                            "value": "CREATE",
                            "description": "Optional filter by action (REGISTER, LOGIN, CREATE, UPDATE, DELETE, COLLECT_REWARD)",
                            "disabled": True,
                        },
                    ],
                    description="Returns the chronological audit log of all actions performed in the family account.",
                ),
            ],
        },
    ]

    variables = [
        {"key": "base_url", "value": "http://localhost:8000", "type": "string"},
        {"key": "access_token", "value": seeded["access_token"], "type": "string"},
        {"key": "refresh_token", "value": seeded["refresh_token"], "type": "string"},
        {"key": "email_parent", "value": DEFAULT_EMAIL, "type": "string"},
        {"key": "password", "value": DEFAULT_PASSWORD, "type": "string"},
        {"key": "name_family", "value": DEFAULT_FAMILY_NAME, "type": "string"},
        {"key": "approve_pin", "value": DEFAULT_APPROVE_PIN, "type": "string"},
        {"key": "reset_code", "value": "000000", "type": "string"},
        {"key": "member_id", "value": DEFAULT_MEMBER_UUID, "type": "string"},
        {"key": "task_id", "value": seeded["task_id"], "type": "string"},
        {"key": "goal_id", "value": seeded["goal_id"], "type": "string"},
        {"key": "reward_id", "value": seeded["reward_id"], "type": "string"},
        {"key": "member_goal_id", "value": seeded["member_goal_id"], "type": "string"},
        {"key": "member_reward_id", "value": seeded["member_reward_id"], "type": "string"},
    ]

    return {
        "info": {
            "_postman_id": "f8a1e7d0-9b4a-4c3e-8d1a-2f5b6c7d8e9f",
            "name": "FHKBackend API (Complete 12-Module Collection)",
            "description": (
                "Ready-to-use Postman Collection for FintechKids Backend (`FHKBackend`).\n\n"
                "- **Pre-configured Bearer JWT (`{{access_token}}`)** at collection level.\n"
                "- **Auto-updating Variables**: Running `Login`, `Register`, `Refresh`, or any `POST` creation endpoint automatically updates `{{access_token}}`, `{{member_id}}`, `{{task_id}}`, `{{goal_id}}`, `{{reward_id}}`, `{{member_goal_id}}`, and `{{member_reward_id}}`."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "auth": {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": "{{access_token}}",
                    "type": "string",
                }
            ],
        },
        "item": folders,
        "variable": variables,
    }


def build_environment(seeded: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        "name": "FHKBackend Local (Development)",
        "values": [
            {"key": "base_url", "value": "http://localhost:8000", "type": "default", "enabled": True},
            {"key": "access_token", "value": seeded["access_token"], "type": "secret", "enabled": True},
            {"key": "refresh_token", "value": seeded["refresh_token"], "type": "secret", "enabled": True},
            {"key": "email_parent", "value": DEFAULT_EMAIL, "type": "default", "enabled": True},
            {"key": "password", "value": DEFAULT_PASSWORD, "type": "default", "enabled": True},
            {"key": "name_family", "value": DEFAULT_FAMILY_NAME, "type": "default", "enabled": True},
            {"key": "approve_pin", "value": DEFAULT_APPROVE_PIN, "type": "default", "enabled": True},
            {"key": "reset_code", "value": "000000", "type": "default", "enabled": True},
            {"key": "member_id", "value": DEFAULT_MEMBER_UUID, "type": "default", "enabled": True},
            {"key": "task_id", "value": seeded["task_id"], "type": "default", "enabled": True},
            {"key": "goal_id", "value": seeded["goal_id"], "type": "default", "enabled": True},
            {"key": "reward_id", "value": seeded["reward_id"], "type": "default", "enabled": True},
            {"key": "member_goal_id", "value": seeded["member_goal_id"], "type": "default", "enabled": True},
            {"key": "member_reward_id", "value": seeded["member_reward_id"], "type": "default", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_at": datetime.now(timezone.utc).isoformat(),
        "_postman_exported_using": "FHKBackend Postman Generator",
    }


def main() -> None:
    seeded = seed_demo_data()
    postman_dir = ROOT_DIR / "postman"
    postman_dir.mkdir(parents=True, exist_ok=True)

    collection_path = postman_dir / "FHKBackend.postman_collection.json"
    environment_path = postman_dir / "FHKBackend.postman_environment.json"

    collection_path.write_text(
        json.dumps(build_collection(seeded), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    environment_path.write_text(
        json.dumps(build_environment(seeded), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Postman Collection generated at: {collection_path}")
    print(f"Postman Environment generated at: {environment_path}")


if __name__ == "__main__":
    main()
