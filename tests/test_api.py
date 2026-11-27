from __future__ import annotations

import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_and_swagger_document():
    # 1. Versioned health check (/api/v1/health) and security headers
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.headers["X-Content-Type-Options"] == "nosniff"

    # 2. Documento OpenAPI / Swagger
    openapi_res = client.get("/api/v1/openapi.json")
    assert openapi_res.status_code == 200
    schema = openapi_res.json()
    assert schema["info"]["title"] == "FHK Backend API"
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/app-version/check" in schema["paths"]
    assert "/api/v1/remote-config" in schema["paths"]
    assert "/api/v1/tasks" in schema["paths"]
    assert "/api/v1/items" not in schema["paths"]


def test_app_version_check_endpoint():
    # 1. Consultar versión desactualizada en iOS (1.0.0 vs 1.2.0 en tienda)
    res_ios = client.get(
        "/api/v1/app-version/check",
        params={"platform": "IOS", "current_version": "1.0.0"},
    )
    assert res_ios.status_code == 200
    data_ios = res_ios.json()
    assert data_ios["platform"] == "IOS"
    assert data_ios["latest_version"] == "1.2.0"
    assert data_ios["is_up_to_date"] is False
    assert data_ios["update_available"] is True
    assert data_ios["force_update"] is False

    # 2. Consultar versión al día en Android (1.2.0 vs 1.2.0 en tienda)
    res_and = client.get(
        "/api/v1/app-version/check",
        params={"platform": "AND", "current_version": "1.2.0"},
    )
    assert res_and.status_code == 200
    data_and = res_and.json()
    assert data_and["platform"] == "AND"
    assert data_and["is_up_to_date"] is True
    assert data_and["update_available"] is False

    # 3. Consultar versión menor a la mínima requerida (0.9.0 < 1.0.0 -> force_update=True)
    res_old = client.get(
        "/api/v1/app-version/check",
        params={"platform": "IOS", "current_version": "0.9.0"},
    )
    assert res_old.status_code == 200
    assert res_old.json()["force_update"] is True


def test_full_auth_and_crud_flow():
    encrypted_password_from_app = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    # 1. Registrar familia / padre con name_family, email_parent, password (encriptado en app) y approve_pin
    register_res = client.post(
        "/api/v1/auth/register",
        json={
            "name_family": "Familia León",
            "email_parent": "fredy@fhk.app",
            "password": encrypted_password_from_app,
            "approve_pin": "1234",
        },
    )
    assert register_res.status_code == 201
    user_data = register_res.json()
    assert user_data["name_family"] == "Familia León"
    assert user_data["email_parent"] == "fredy@fhk.app"
    assert user_data["approve_pin"] == "1234"
    assert "hashed_password" not in user_data
    assert "password" not in user_data
    assert "created_at" in user_data and user_data["created_at"] is not None

    # 2. Iniciar sesión (Login) con email_parent y el mismo password encriptado
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email_parent": "fredy@fhk.app",
            "password": encrypted_password_from_app,
        },
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert tokens["approve_pin"] == "1234"
    assert tokens["name_family"] == "Familia León"
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Acceder a ruta protegida (/users/me)
    me_res = client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["name_family"] == "Familia León"

    # 3.1 Crear un miembro de la familia vinculado al padre y a su name_family
    member_uuid = "550e8400-e29b-41d4-a716-446655440000"
    create_member_res = client.post(
        "/api/v1/family-members",
        headers=headers,
        json={
            "email_parent": "fredy@fhk.app",
            "identification_uuid": member_uuid,
            "member_name": "Mateo León",
            "avatar_name": "avatar_lion_01",
            "name_family": me_res.json()["name_family"],
        },
    )
    assert create_member_res.status_code == 201
    member_data = create_member_res.json()
    assert member_data["identification_uuid"] == member_uuid
    assert member_data["member_name"] == "Mateo León"
    assert member_data["name_family"] == "Familia León"
    assert member_data["parent_id"] == user_data["id"]

    # 3.2 Listar miembros de la familia
    list_members_res = client.get("/api/v1/family-members", headers=headers)
    assert list_members_res.status_code == 200
    assert len(list_members_res.json()) == 1

    # 3.3 Editar nombre y avatar de un miembro de la familia por su identification_uuid
    patch_member_res = client.patch(
        f"/api/v1/family-members/{member_uuid}",
        headers=headers,
        json={
            "member_name": "Mateo León Editado",
            "avatar_name": "avatar_tiger_02",
        },
    )
    assert patch_member_res.status_code == 200
    patched_member = patch_member_res.json()
    assert patched_member["member_name"] == "Mateo León Editado"
    assert patched_member["avatar_name"] == "avatar_tiger_02"

    # 3.4 Eliminar miembro de la familia por su identification_uuid
    delete_member_res = client.delete(
        f"/api/v1/family-members/{member_uuid}",
        headers=headers,
    )
    assert delete_member_res.status_code == 200
    assert delete_member_res.json()["identification_uuid"] == member_uuid

    list_after_del = client.get("/api/v1/family-members", headers=headers)
    assert list_after_del.status_code == 200
    assert len(list_after_del.json()) == 0

    # 3.5 Crear una meta (Goal) vinculada al padre
    create_goal_res = client.post(
        "/api/v1/goals",
        headers=headers,
        json={
            "measure_type": "minutes",
            "status": "active",
            "email_parent": "fredy@fhk.app",
            "name": "Lectura diaria",
            "value": 30,
        },
    )
    assert create_goal_res.status_code == 201
    goal_data = create_goal_res.json()
    assert goal_data["measure_type"] == "minutes"
    assert goal_data["status"] == "active"
    assert goal_data["email_parent"] == "fredy@fhk.app"
    assert goal_data["name"] == "Lectura diaria"
    assert goal_data["value"] == 30
    assert goal_data["parent_id"] == user_data["id"]
    assert "created_at" in goal_data and goal_data["created_at"] is not None

    # 3.6 Listar metas
    list_goals_res = client.get("/api/v1/goals?status=active", headers=headers)
    assert list_goals_res.status_code == 200
    assert len(list_goals_res.json()) == 1

    # 3.6.1 Crear nuevamente un miembro para asignarle la meta creada por el padre
    member_for_goal_uuid = "660e8400-e29b-41d4-a716-446655440111"
    client.post(
        "/api/v1/family-members",
        headers=headers,
        json={
            "email_parent": "fredy@fhk.app",
            "identification_uuid": member_for_goal_uuid,
            "member_name": "Sofía León",
            "avatar_name": "avatar_unicorn_01",
            "name_family": "Familia León",
        },
    )

    # 3.6.2 Asignar / Crear una meta para un miembro de la familia (POST /api/v1/member-goals)
    goal_id = goal_data["id"]
    create_member_goal_res = client.post(
        "/api/v1/member-goals",
        headers=headers,
        json={
            "goal_id": goal_id,
            "member_id": member_for_goal_uuid,
            "rewards_system_type": "stars",
            "rewards_system_value": 10,
            "accumulated_value": 0,
            "parent_email": "fredy@fhk.app",
            "name": "Lectura diaria",
        },
    )
    assert create_member_goal_res.status_code == 201
    mg_data = create_member_goal_res.json()
    assert mg_data["goal_id"] == goal_id
    assert mg_data["member_id"] == member_for_goal_uuid
    assert mg_data["rewards_system_type"] == "stars"
    assert mg_data["rewards_system_value"] == 10
    assert mg_data["accumulated_value"] == 0
    assert mg_data["parent_email"] == "fredy@fhk.app"
    assert mg_data["name"] == "Lectura diaria"
    assert "created_at" in mg_data and mg_data["created_at"] is not None

    # 3.6.3 Consultar metas del miembro
    list_mg_res = client.get(
        f"/api/v1/member-goals?member_id={member_for_goal_uuid}",
        headers=headers,
    )
    assert list_mg_res.status_code == 200
    assert len(list_mg_res.json()) == 1

    # 3.6.4 Actualizar progreso (accumulated_value) de la meta del miembro
    member_goal_id = mg_data["id"]
    patch_mg_res = client.patch(
        f"/api/v1/member-goals/{member_goal_id}",
        headers=headers,
        json={"accumulated_value": 25},
    )
    assert patch_mg_res.status_code == 200
    assert patch_mg_res.json()["accumulated_value"] == 25

    # 3.6.5 Eliminar la meta del miembro
    del_mg_res = client.delete(
        f"/api/v1/member-goals/{member_goal_id}",
        headers=headers,
    )
    assert del_mg_res.status_code == 200
    assert del_mg_res.json()["member_goal_id"] == member_goal_id

    list_mg_after_del = client.get(
        f"/api/v1/member-goals?member_id={member_for_goal_uuid}",
        headers=headers,
    )
    assert list_mg_after_del.status_code == 200
    assert len(list_mg_after_del.json()) == 0

    # 3.6.6 Registrar balance del miembro (POST /api/v1/member-balances)
    create_balance_res = client.post(
        "/api/v1/member-balances",
        headers=headers,
        json={
            "member_id": member_for_goal_uuid,
            "coins_obtained": 150,
            "time_obtained": "01:30:00",
        },
    )
    assert create_balance_res.status_code == 201
    balance_data = create_balance_res.json()
    assert balance_data["member_id"] == member_for_goal_uuid
    assert balance_data["coins_obtained"] == 150
    assert balance_data["time_obtained"] == "01:30:00"
    assert "created_at" in balance_data and balance_data["created_at"] is not None

    # 3.6.7 Actualizar balance del miembro (PATCH /api/v1/member-balances/{member_id})
    patch_balance_res = client.patch(
        f"/api/v1/member-balances/{member_for_goal_uuid}",
        headers=headers,
        json={"coins_obtained": 220, "time_obtained": "02:15:00"},
    )
    assert patch_balance_res.status_code == 200
    assert patch_balance_res.json()["coins_obtained"] == 220
    assert patch_balance_res.json()["time_obtained"] == "02:15:00"

    # 3.6.7b Obtener el saldo de un miembro en concreto (GET /api/v1/member-balances/{member_id})
    get_single_balance_res = client.get(
        f"/api/v1/member-balances/{member_for_goal_uuid}",
        params={"email_parent": "fredy@fhk.app"},
        headers=headers,
    )
    assert get_single_balance_res.status_code == 200
    single_balance = get_single_balance_res.json()
    assert single_balance["member_id"] == member_for_goal_uuid
    assert single_balance["coins_obtained"] == 220
    assert single_balance["time_obtained"] == "02:15:00"

    # 3.6.8 Listar balances del miembro
    list_balance_res = client.get(
        f"/api/v1/member-balances?member_id={member_for_goal_uuid}",
        headers=headers,
    )
    assert list_balance_res.status_code == 200
    assert len(list_balance_res.json()) == 1

    # 3.6.9 Crear una recompensa del padre (POST /api/v1/rewards)
    create_reward_res = client.post(
        "/api/v1/rewards",
        headers=headers,
        json={
            "name": "1 hora de videojuegos",
            "time_required": "01:00:00",
            "coins_required": 100,
            "email_parent": "fredy@fhk.app",
        },
    )
    assert create_reward_res.status_code == 201
    reward_data = create_reward_res.json()
    assert reward_data["name"] == "1 hora de videojuegos"
    assert reward_data["time_required"] == "01:00:00"
    assert reward_data["coins_required"] == 100
    assert reward_data["email_parent"] == "fredy@fhk.app"
    assert "created_at" in reward_data and reward_data["created_at"] is not None

    # 3.6.10 Listar recompensas del padre (GET /api/v1/rewards)
    list_rewards_res = client.get("/api/v1/rewards", headers=headers)
    assert list_rewards_res.status_code == 200
    assert len(list_rewards_res.json()) == 1

    # 3.6.11 Editar recompensa del padre (PATCH /api/v1/rewards/{reward_id})
    reward_id = reward_data["id"]
    patch_reward_res = client.patch(
        f"/api/v1/rewards/{reward_id}",
        headers=headers,
        json={
            "name": "2 horas de videojuegos",
            "time_required": "02:00:00",
            "coins_required": 180,
        },
    )
    assert patch_reward_res.status_code == 200
    patched_reward = patch_reward_res.json()
    assert patched_reward["name"] == "2 horas de videojuegos"
    assert patched_reward["time_required"] == "02:00:00"
    assert patched_reward["coins_required"] == 180

    # 3.6.11b Miembro reclama recompensa enviando reward_id (el backend resuelve name_reward automáticamente)
    create_mr_res = client.post(
        "/api/v1/member-rewards",
        headers=headers,
        json={
            "member_id": member_for_goal_uuid,
            "parent_email": "fredy@fhk.app",
            "reward_id": reward_id,
            "claimed_value": "180 coins",
            "state": "PENDING",
        },
    )
    assert create_mr_res.status_code == 201
    mr_data = create_mr_res.json()
    member_reward_id = mr_data["id"]
    assert mr_data["reward_id"] == reward_id
    assert mr_data["name_reward"] == "2 horas de videojuegos"
    assert mr_data["state"] == "PENDING"
    assert "created_at" in mr_data and mr_data["created_at"] is not None

    # 3.6.11c Padre cambia estado a COLLECTED (o COLLETED) cuando entrega la recompensa
    patch_mr_res = client.patch(
        f"/api/v1/member-rewards/{member_reward_id}",
        headers=headers,
        json={"state": "COLLECTED"},
    )
    assert patch_mr_res.status_code == 200
    assert patch_mr_res.json()["state"] == "COLLECTED"

    # 3.6.11d Eliminar la recompensa ya cobrada
    del_mr_res = client.delete(
        f"/api/v1/member-rewards/{member_reward_id}",
        headers=headers,
    )
    assert del_mr_res.status_code == 200
    assert del_mr_res.json()["member_reward_id"] == member_reward_id

    # 3.6.12 Eliminar recompensa del padre (DELETE /api/v1/rewards/{reward_id})
    del_reward_res = client.delete(f"/api/v1/rewards/{reward_id}", headers=headers)
    assert del_reward_res.status_code == 200
    assert del_reward_res.json()["reward_id"] == reward_id

    list_rewards_after_del = client.get("/api/v1/rewards", headers=headers)
    assert list_rewards_after_del.status_code == 200
    assert len(list_rewards_after_del.json()) == 0

    # 3.6.13 Crear dos tareas familiares (POST /api/v1/tasks) — por defecto status='enable'
    task1_res = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "name": "Ordenar la habitación",
            "time_granted": "00:30:00",
            "coins_granted": 50,
            "email_parent": "fredy@fhk.app",
            "description": "Tender la cama y guardar los juguetes.",
        },
    )
    assert task1_res.status_code == 201
    task1_data = task1_res.json()
    task1_id = task1_data["id"]
    assert task1_data["status"] == "enable"
    assert "created_at" in task1_data and task1_data["created_at"] is not None

    task2_res = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "name": "Lavar los platos",
            "time_granted": "00:20:00",
            "coins_granted": 35,
            "email_parent": "fredy@fhk.app",
            "description": "Lavar los platos después de la cena.",
        },
    )
    assert task2_res.status_code == 201
    task2_id = task2_res.json()["id"]

    # 3.6.14 Editar la segunda tarea y deshabilitarla (status='disable')
    patch_task2_res = client.patch(
        f"/api/v1/tasks/{task2_id}",
        headers=headers,
        json={
            "name": "Lavar y secar los platos",
            "coins_granted": 40,
            "status": "disable",
        },
    )
    assert patch_task2_res.status_code == 200
    assert patch_task2_res.json()["status"] == "disable"
    assert patch_task2_res.json()["coins_granted"] == 40

    # 3.6.15 Listar todas las tareas de la familia con cualquier estado (GET /api/v1/tasks)
    all_tasks_res = client.get("/api/v1/tasks", headers=headers)
    assert all_tasks_res.status_code == 200
    assert len(all_tasks_res.json()) == 2

    # 3.6.16 Listar tareas de la familia solo con estado 'enable' (GET /api/v1/tasks/enabled)
    enabled_tasks_res = client.get("/api/v1/tasks/enabled", headers=headers)
    assert enabled_tasks_res.status_code == 200
    assert len(enabled_tasks_res.json()) == 1
    assert enabled_tasks_res.json()[0]["id"] == task1_id
    assert enabled_tasks_res.json()[0]["status"] == "enable"

    # 3.6.17 Eliminar una tarea de la familia (DELETE /api/v1/tasks/{task_id})
    del_task1_res = client.delete(f"/api/v1/tasks/{task1_id}", headers=headers)
    assert del_task1_res.status_code == 200
    assert del_task1_res.json()["task_id"] == task1_id

    # 3.7 Editar meta del padre (PATCH /api/v1/goals/{goal_id})
    patch_goal_res = client.patch(
        f"/api/v1/goals/{goal_id}",
        headers=headers,
        json={
            "name": "Lectura nocturna",
            "value": 45,
            "status": "inactive",
        },
    )
    assert patch_goal_res.status_code == 200
    patched_goal = patch_goal_res.json()
    assert patched_goal["name"] == "Lectura nocturna"
    assert patched_goal["value"] == 45
    assert patched_goal["status"] == "inactive"

    # 3.8 Eliminar meta del padre (DELETE /api/v1/goals/{goal_id})
    del_goal_res = client.delete(f"/api/v1/goals/{goal_id}", headers=headers)
    assert del_goal_res.status_code == 200
    assert del_goal_res.json()["goal_id"] == goal_id

    list_goals_after_del = client.get("/api/v1/goals", headers=headers)
    assert list_goals_after_del.status_code == 200
    assert len(list_goals_after_del.json()) == 0

    # 3.9 Verificar que el historial de actividad (Audit Log) registró automáticamente las acciones
    logs_res = client.get("/api/v1/activity-logs", headers=headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 10
    recorded_actions = {entry["action"] for entry in logs}
    assert "REGISTER_FAMILY" in recorded_actions
    assert "CREATE_MEMBER" in recorded_actions
    assert "CREATE_GOAL" in recorded_actions
    assert "CREATE_MEMBER_BALANCE" in recorded_actions
    assert "CLAIM_MEMBER_REWARD" in recorded_actions
    assert "UPDATE_MEMBER_REWARD_STATE" in recorded_actions
    assert "CREATE_TASK" in recorded_actions

    # 4. Renovar token con Refresh Token
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()


def test_password_recovery_flow():
    # 1. Solicitar código temporal de 6 dígitos con email_parent
    forgot_res = client.post(
        "/api/v1/auth/forgot-password",
        json={"email_parent": "fredy@fhk.app"},
    )
    assert forgot_res.status_code == 200
    forgot_data = forgot_res.json()
    recovery_code = forgot_data["debug_recovery_code"]
    assert len(recovery_code) == 6
    assert recovery_code.isdigit()

    # 2. Confirmar el código de 6 dígitos y establecer el nuevo password encriptado desde la app
    new_encrypted_password = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    reset_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email_parent": "fredy@fhk.app",
            "recovery_code": recovery_code,
            "new_password": new_encrypted_password,
        },
    )
    assert reset_res.status_code == 200

    # 3. Verificar que el código de 6 dígitos ya no se pueda reutilizar una segunda vez
    reuse_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email_parent": "fredy@fhk.app",
            "recovery_code": recovery_code,
            "new_password": new_encrypted_password,
        },
    )
    assert reuse_res.status_code == 400
    assert reuse_res.json()["error_code"] == "RECOVERY_CODE_NOT_REQUESTED"

    # 4. Iniciar sesión con el nuevo password encriptado
    login_new_res = client.post(
        "/api/v1/auth/login",
        json={
            "email_parent": "fredy@fhk.app",
            "password": new_encrypted_password,
        },
    )
    assert login_new_res.status_code == 200
    assert "access_token" in login_new_res.json()


def test_protected_endpoints_reject_without_valid_token():
    invalid_headers = {"Authorization": "Bearer token-invalido-o-expirado"}
    protected_gets = [
        "/api/v1/users/me",
        "/api/v1/family-members",
        "/api/v1/goals",
        "/api/v1/member-goals",
        "/api/v1/member-balances",
        "/api/v1/rewards",
        "/api/v1/member-rewards",
        "/api/v1/tasks",
        "/api/v1/tasks/enabled",
        "/api/v1/activity-logs",
    ]
    for path in protected_gets:
        # Sin token -> 401 + INVALID_OR_EXPIRED_TOKEN
        res_no_token = client.get(path)
        assert res_no_token.status_code == 401
        assert res_no_token.json()["error_code"] == "INVALID_OR_EXPIRED_TOKEN"
        # Con token inválido -> 401 + INVALID_OR_EXPIRED_TOKEN
        res_bad_token = client.get(path, headers=invalid_headers)
        assert res_bad_token.status_code == 401
        assert res_bad_token.json()["error_code"] == "INVALID_OR_EXPIRED_TOKEN"


def test_controlled_error_codes_across_endpoints():
    # 1. Duplicate registration -> EMAIL_ALREADY_REGISTERED (400)
    dup_res = client.post(
        "/api/v1/auth/register",
        json={
            "name_family": "Familia León",
            "email_parent": "fredy@fhk.app",
            "password": "some_password",
            "approve_pin": "1234",
        },
    )
    assert dup_res.status_code == 400
    assert dup_res.json()["error_code"] == "EMAIL_ALREADY_REGISTERED"

    # 2. Wrong password -> INVALID_CREDENTIALS (401)
    bad_login = client.post(
        "/api/v1/auth/login",
        json={
            "email_parent": "fredy@fhk.app",
            "password": "wrong_password_123",
        },
    )
    assert bad_login.status_code == 401
    assert bad_login.json()["error_code"] == "INVALID_CREDENTIALS"

    # 3. Unknown email on forgot-password -> USER_NOT_FOUND (404)
    missing_user = client.post(
        "/api/v1/auth/forgot-password",
        json={"email_parent": "nobody@fhk.app"},
    )
    assert missing_user.status_code == 404
    assert missing_user.json()["error_code"] == "USER_NOT_FOUND"

    # 4. Wrong 6-digit recovery code -> INVALID_RECOVERY_CODE (400)
    client.post("/api/v1/auth/forgot-password", json={"email_parent": "fredy@fhk.app"})
    wrong_code = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email_parent": "fredy@fhk.app",
            "recovery_code": "000000",
            "new_password": "new_password_1234",
        },
    )
    assert wrong_code.status_code == 400
    assert wrong_code.json()["error_code"] == "INVALID_RECOVERY_CODE"

    # 5. Validation error -> VALIDATION_ERROR (422)
    validation_res = client.post(
        "/api/v1/auth/login",
        json={"email_parent": "not-an-email"},
    )
    assert validation_res.status_code == 422
    validation_body = validation_res.json()
    assert validation_body["error_code"] == "VALIDATION_ERROR"
    assert isinstance(validation_body["errors"], list)

    # 6. Protected resource not found -> TASK_NOT_FOUND (404)
    login_ok = client.post(
        "/api/v1/auth/login",
        json={
            "email_parent": "fredy@fhk.app",
            "password": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        },
    )
    token = login_ok.json()["access_token"]
    missing_task = client.patch(
        "/api/v1/tasks/999999",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Does not exist"},
    )
    assert missing_task.status_code == 404
    assert missing_task.json()["error_code"] == "TASK_NOT_FOUND"


def test_forgot_password_production_email_delivery(monkeypatch):
    import httpx
    from app.core import email as email_module
    from app.core.config import settings

    # 1. Production without RESEND_API_KEY -> 503 EMAIL_SERVICE_NOT_CONFIGURED
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")

    unconfigured_res = client.post(
        "/api/v1/auth/forgot-password",
        json={"email_parent": "fredy@fhk.app"},
    )
    assert unconfigured_res.status_code == 503
    assert unconfigured_res.json()["error_code"] == "EMAIL_SERVICE_NOT_CONFIGURED"

    # 2. Production with RESEND_API_KEY and Resend 200 OK -> sends email and hides debug_recovery_code
    captured_requests = []

    class DummyResponse:
        def __init__(self, status_code: int, text: str = "{}"):
            self.status_code = status_code
            self.text = text

    def fake_post_success(url, *, headers=None, json=None, timeout=None):
        captured_requests.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return DummyResponse(200, '{"id": "email_test_123"}')

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test_fake_key_123")
    monkeypatch.setattr(settings, "EMAIL_FROM", "FintechKids <no-reply@fhk.app>")
    monkeypatch.setattr(email_module.httpx, "post", fake_post_success)

    prod_res = client.post(
        "/api/v1/auth/forgot-password",
        json={"email_parent": "fredy@fhk.app"},
    )
    assert prod_res.status_code == 200
    prod_body = prod_res.json()
    assert prod_body["debug_recovery_code"] is None
    assert len(captured_requests) == 1

    sent = captured_requests[0]
    assert sent["url"] == email_module.RESEND_EMAILS_URL
    assert sent["headers"]["Authorization"] == "Bearer re_test_fake_key_123"
    assert sent["json"]["from"] == "FintechKids <no-reply@fhk.app>"
    assert sent["json"]["to"] == ["fredy@fhk.app"]

    # Extract 6-digit code from the plain text body and verify /reset-password accepts it
    import re

    match = re.search(r"\b(\d{6})\b", sent["json"]["text"])
    assert match is not None
    emailed_code = match.group(1)
    assert emailed_code in sent["json"]["html"]

    reset_res = client.post(
        "/api/v1/auth/reset-password",
        json={
            "email_parent": "fredy@fhk.app",
            "recovery_code": emailed_code,
            "new_password": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        },
    )
    assert reset_res.status_code == 200

    # 3. Resend rejects with 403 or network error -> 502 EMAIL_DELIVERY_FAILED
    def fake_post_rejected(url, *, headers=None, json=None, timeout=None):
        return DummyResponse(403, '{"message": "Domain not verified"}')

    monkeypatch.setattr(email_module.httpx, "post", fake_post_rejected)
    rejected_res = client.post(
        "/api/v1/auth/forgot-password",
        json={"email_parent": "fredy@fhk.app"},
    )
    assert rejected_res.status_code == 502
    assert rejected_res.json()["error_code"] == "EMAIL_DELIVERY_FAILED"

    def fake_post_network_error(url, *, headers=None, json=None, timeout=None):
        raise httpx.ConnectError("Network unreachable")

    monkeypatch.setattr(email_module.httpx, "post", fake_post_network_error)
    network_err_res = client.post(
        "/api/v1/auth/forgot-password",
        json={"email_parent": "fredy@fhk.app"},
    )
    assert network_err_res.status_code == 502
    assert network_err_res.json()["error_code"] == "EMAIL_DELIVERY_FAILED"


def test_remote_config_endpoints():
    # 1. Public GET returns auto-seeded defaults matching Firebase Remote Config structure
    get_res = client.get("/api/v1/remote-config")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["cached_time_expiration"] == 5
    assert data["enabled_languages"] == {"es": True, "fr": True, "en": True, "it": True}
    assert data["menus_bottom_bar_enables"] == [
        {
            "id": 1,
            "name": "payments",
            "icon": "payments-icon",
            "label_localized_key": "key_payments_title",
            "active": True,
        }
    ]
    assert "updated_at" in data

    # 2. Unauthenticated PUT is rejected with INVALID_OR_EXPIRED_TOKEN (401)
    unauth_put = client.put(
        "/api/v1/remote-config",
        json={"cached_time_expiration": 10},
    )
    assert unauth_put.status_code == 401
    assert unauth_put.json()["error_code"] == "INVALID_OR_EXPIRED_TOKEN"

    # 3. Authenticated PUT updates languages, menu flags, and cache expiration
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email_parent": "fredy@fhk.app",
            "password": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        },
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    put_res = client.put(
        "/api/v1/remote-config",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "cached_time_expiration": 10,
            "enabled_languages": {"es": True, "fr": False, "en": True, "it": False},
            "menus_bottom_bar_enables": [
                {
                    "id": 1,
                    "name": "payments",
                    "icon": "payments-icon",
                    "label_localized_key": "key_payments_title",
                    "active": True,
                },
                {
                    "id": 2,
                    "name": "rewards",
                    "icon": "rewards-icon",
                    "label_localized_key": "key_rewards_title",
                    "active": False,
                },
            ],
        },
    )
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["cached_time_expiration"] == 10
    assert updated["enabled_languages"] == {"es": True, "fr": False, "en": True, "it": False}
    assert len(updated["menus_bottom_bar_enables"]) == 2
    assert updated["menus_bottom_bar_enables"][1]["active"] is False

    # 4. Partial PUT keeps untouched fields
    partial_put = client.put(
        "/api/v1/remote-config",
        headers={"Authorization": f"Bearer {token}"},
        json={"cached_time_expiration": 3},
    )
    assert partial_put.status_code == 200
    assert partial_put.json()["cached_time_expiration"] == 3
    assert partial_put.json()["enabled_languages"] == {"es": True, "fr": False, "en": True, "it": False}

    # 5. Duplicate menu item id triggers controlled VALIDATION_ERROR (422)
    dup_put = client.put(
        "/api/v1/remote-config",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "menus_bottom_bar_enables": [
                {
                    "id": 1,
                    "name": "payments",
                    "icon": "payments-icon",
                    "label_localized_key": "key_payments_title",
                    "active": True,
                },
                {
                    "id": 1,
                    "name": "duplicate",
                    "icon": "dup-icon",
                    "label_localized_key": "key_dup_title",
                    "active": True,
                },
            ]
        },
    )
    assert dup_put.status_code == 422
    assert dup_put.json()["error_code"] == "VALIDATION_ERROR"
