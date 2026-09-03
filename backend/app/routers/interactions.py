"""/api/interactions - search the message log across every case."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..serializers import interaction_out

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.get("", response_model=schemas.Page[schemas.InteractionOut])
def search_interactions(
    q: str | None = Query(default=None, description="substring match on the summary"),
    case_id: int | None = None,
    actor_id: int | None = Query(default=None, description="via the contact or the case link"),
    direction: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(models.Interaction).options(
        selectinload(models.Interaction.contact),
        selectinload(models.Interaction.case),
    )
    if q:
        stmt = stmt.where(models.Interaction.summary.ilike(f"%{q}%"))
    if case_id is not None:
        stmt = stmt.where(models.Interaction.case_id == case_id)
    if direction:
        stmt = stmt.where(models.Interaction.direction == direction)
    if actor_id is not None:
        by_contact = select(models.Contact.id).where(models.Contact.actor_id == actor_id)
        by_case = select(models.CaseActor.case_id).where(models.CaseActor.actor_id == actor_id)
        stmt = stmt.where(
            or_(
                models.Interaction.contact_id.in_(by_contact),
                models.Interaction.case_id.in_(by_case),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(
        stmt.order_by(models.Interaction.occurred_at.desc()).limit(limit).offset(offset)
    ).all()
    return schemas.Page(
        items=[interaction_out(i, with_case=True) for i in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
