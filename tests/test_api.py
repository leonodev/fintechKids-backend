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
    # 1. Registrar usuario
    register_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "fredy@fhk.app",
            "full_name": "Fredy León",
            "password": "PasswordSeguro123!",
        },
    )
    assert register_res.status_code == 201
    user_data = register_res.json()
    assert user_data["email"] == "fredy@fhk.app"
    assert "hashed_password" not in user_data

    # 2. Iniciar sesión (Login)
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "fredy@fhk.app",
            "password": "PasswordSeguro123!",
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
    assert me_res.json()["full_name"] == "Fredy León"

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
