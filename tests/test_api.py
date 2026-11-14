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
