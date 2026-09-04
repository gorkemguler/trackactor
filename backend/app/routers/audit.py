"""/api/audit - read the audit trail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=schemas.Page[schemas.AuditEventOut])
def list_audit(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(models.AuditEvent)
    if entity_type:
        stmt = stmt.where(models.AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(models.AuditEvent.entity_id == entity_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(models.AuditEvent.at.desc()).limit(limit).offset(offset)
    ).all()
    return schemas.Page(
        items=[schemas.AuditEventOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
