"""Database engine, session factory and declarative base."""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

connect_args = {"check_same_thread": False} if settings.db_url.startswith("sqlite") else {}

engine = create_engine(settings.db_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Bring the schema to head via Alembic. Safe to call on every startup.

    A database created by an older create_all build has the tables but no
    alembic_version row - stamp it at the baseline first so the upgrade only
    applies what came after.
    """
    from alembic import command
    from alembic.config import Config

    from . import models  # noqa: F401  (register tables on Base.metadata)

    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(_BACKEND_DIR, "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.db_url)

    insp = inspect(engine)
    if insp.has_table("cases") and not insp.has_table("alembic_version"):
        command.stamp(cfg, "0001_baseline")
    command.upgrade(cfg, "head")
