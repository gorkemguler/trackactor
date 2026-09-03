"""/api/stats — dashboard counters."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..serializers import interaction_out

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=schemas.Stats)
def get_stats(db: Session = Depends(get_db)):
    total_cases = db.scalar(select(func.count(models.Case.id))) or 0
    total_actors = db.scalar(select(func.count(models.Actor.id))) or 0
    total_contacts = db.scalar(select(func.count(models.Contact.id))) or 0
    total_interactions = db.scalar(select(func.count(models.Interaction.id))) or 0

    status_rows = db.execute(
        select(models.Case.status, func.count(models.Case.id)).group_by(models.Case.status)
    ).all()
    cases_by_status = [
        schemas.StatusCount(status=s, count=c) for s, c in sorted(status_rows)
    ]
    awaiting = next(
        (c for s, c in status_rows if s == "awaiting_response"), 0
    )

    cases_without_interaction = db.scalar(
        select(func.count(models.Case.id)).where(
            ~models.Case.id.in_(select(models.Interaction.case_id).distinct())
        )
    ) or 0

    recent_inbound = db.scalars(
        select(models.Interaction)
        .options(selectinload(models.Interaction.contact))
        .where(models.Interaction.direction == "inbound")
        .order_by(models.Interaction.occurred_at.desc())
        .limit(10)
    ).all()

    return schemas.Stats(
        total_cases=total_cases,
        total_actors=total_actors,
        total_contacts=total_contacts,
        total_interactions=total_interactions,
        cases_by_status=cases_by_status,
        awaiting_response=awaiting,
        cases_without_interaction=cases_without_interaction,
        recent_inbound=[interaction_out(i) for i in recent_inbound],
    )
