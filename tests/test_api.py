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
    # 1. Health check y cabeceras de seguridad
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.headers["X-Content-Type-Options"] == "nosniff"

    # 2. Documento OpenAPI / Swagger
    openapi_res = client.get("/api/v1/openapi.json")
    assert openapi_res.status_code == 200
    schema = openapi_res.json()
    assert schema["info"]["title"] == "FHK Backend API"
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/app-version/check" in schema["paths"]
    assert "/api/v1/items" in schema["paths"]


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

    # 4. Crear un elemento persistido en BD
    create_item_res = client.post(
        "/api/v1/items",
        headers=headers,
        json={
            "title": "Mi primer servicio",
            "description": "Creado desde la app",
            "price": 29.99,
            "is_completed": False,
        },
    )
    assert create_item_res.status_code == 201
    item_id = create_item_res.json()["id"]

    # 5. Listar elementos
    list_res = client.get("/api/v1/items", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 6. Actualizar elemento
    patch_res = client.patch(
        f"/api/v1/items/{item_id}",
        headers=headers,
        json={"is_completed": True},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_completed"] is True

    # 7. Renovar token con Refresh Token
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.json()

    # 8. Eliminar elemento
    del_res = client.delete(f"/api/v1/items/{item_id}", headers=headers)
    assert del_res.status_code == 204


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
    ]
    for path in protected_gets:
        # Sin token -> 401
        res_no_token = client.get(path)
        assert res_no_token.status_code == 401
        # Con token inválido -> 401
        res_bad_token = client.get(path, headers=invalid_headers)
        assert res_bad_token.status_code == 401
