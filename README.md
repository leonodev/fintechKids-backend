# FHK Backend API

Backend REST construido con **Python + FastAPI**, **SQLAlchemy 2.0** (SQLite en desarrollo / PostgreSQL en producción), autenticación **JWT (Access + Refresh Token)** con contraseñas encriptadas (`bcrypt`) y generación automática de documentación **Swagger / OpenAPI 3.1**.

---

## 1. Inicio Rápido

```bash
# 1. Activar el entorno virtual
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Levantar el servidor en modo desarrollo (con recarga automática)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Una vez iniciado el servidor, abre en tu navegador:
- **Swagger UI Interactivo**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Documento OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json
- **Health Check**: http://localhost:8000/health

---

## 2. Exportar el archivo `openapi.json` en cualquier momento

Cada vez que agregues o modifiques un endpoint, el Swagger en `/docs` se actualiza en tiempo real. Si además quieres guardar/actualizar el archivo físico `openapi.json` en la raíz del proyecto (por ejemplo, para importarlo en Postman o en un generador de código en tu App):

```bash
python3 scripts/export_openapi.py
```

---

## 3. Cómo agregar un nuevo Endpoint (y que se actualice el Swagger solo)

1. **Modelo de Base de Datos**: Crea tu tabla en `app/models/mi_entidad.py` e impórtala en `app/models/__init__.py`.
2. **Esquema (DTO)**: Crea los modelos Pydantic de entrada y salida en `app/schemas/mi_entidad.py` (FastAPI usará estos tipos para documentar el Swagger automáticamente).
3. **Rutas (Endpoints)**: Crea el archivo `app/api/v1/endpoints/mi_entidad.py` usando `Depends(get_current_user)` para protegerlo con JWT.
4. **Registro**: Incluye el router en `app/api/v1/router.py`.

---

## 4. Pasar de SQLite (Local) a PostgreSQL (Producción)

Solo cambia la variable `DATABASE_URL` en tu archivo `.env`:

```env
DATABASE_URL="postgresql://usuario:password@tu-servidor:5432/fhk_db"
```
