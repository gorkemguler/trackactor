"""Append-only audit trail. record() is called explicitly from the routes that
change things, with a before/after diff on updates."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from . import models
from .security import SESSION_COOKIE


def _actor_label(request: Request, db: Session) -> tuple[int | None, str]:
    user = getattr(request.state, "user", None)
    if user is None:
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            s = db.get(models.Session, token)
            if s is not None:
                user = s.user
    if user is not None:
        return user.id, user.username
    if request.headers.get("x-api-key"):
        return None, "api-key"
    return None, "anon"


def _jsonable(v: Any) -> Any:
    return v if isinstance(v, (str, int, float, bool, type(None), list, dict)) else str(v)


def diff(before: dict[str, Any], data: dict[str, Any]) -> dict[str, list]:
    """{'status': ['open', 'closed']} for every field in `data` that changed."""
    out: dict[str, list] = {}
    for field, new in data.items():
        old = before.get(field)
        if old != new:
            out[field] = [_jsonable(old), _jsonable(new)]
    return out


def record(
    db: Session,
    request: Request,
    *,
    action: str,
    entity_type: str,
    entity_id: int | None,
    summary: str = "",
    changes: dict | None = None,
) -> None:
    user_id, label = _actor_label(request, db)
    db.add(
        models.AuditEvent(
            user_id=user_id,
            user_label=label,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            changes=changes or {},
        )
    )
