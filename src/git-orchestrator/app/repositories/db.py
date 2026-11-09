"""Database engine, session factory, and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import settings
from ..models.ops import Base

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Synchronous context manager yielding a DB session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_db() -> AsyncGenerator[Session, None]:
    """FastAPI dependency yielding a committed DB session."""
    with get_db_context() as db:
        yield db


def init_db() -> None:
    """Create all tables owned by this adapter (dev/test helper)."""
    Base.metadata.create_all(bind=engine)
