from __future__ import annotations

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Normalize postgres:// to postgresql:// for SQLAlchemy 2.0 compatibility on cloud providers
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# If using SQLite, check_same_thread=False is required for FastAPI
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependencia para obtener una sesión de base de datos por petición HTTP."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
