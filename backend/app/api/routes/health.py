"""Liveness and readiness endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Does not touch external dependencies."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Readiness probe. Verifies the database is reachable."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return {"status": "degraded", "database": "unavailable"}
    return {"status": "ok", "database": "ok"}
