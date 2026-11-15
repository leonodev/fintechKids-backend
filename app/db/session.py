from __future__ import annotations

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Normalize postgres:// and postgresql:// to postgresql+psycopg2://
# because SQLAlchemy 2.1+ defaults bare postgresql:// to psycopg v3 instead of psycopg2
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

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
