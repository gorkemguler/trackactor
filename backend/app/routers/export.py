"""/api/export - flat CSV dumps for reporting."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models
from ..database import get_db

router = APIRouter(prefix="/api/export", tags=["export"])


def _csv(rows: list[dict], fields: list[str], filename: str) -> Response:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cases.csv")
def cases_csv(db: Session = Depends(get_db)):
    fields = [
        "case_id", "title", "status", "priority", "source_platform", "source_url",
        "analyst", "assignee", "created_by", "tags", "actors", "interactions",
        "last_interaction_at", "created_at", "updated_at",
    ]
    cases = db.scalars(
        select(models.Case).options(
            selectinload(models.Case.actor_links).selectinload(models.CaseActor.actor),
            selectinload(models.Case.interactions),
            selectinload(models.Case.assignee),
            selectinload(models.Case.created_by),
        ).order_by(models.Case.created_at)
    ).all()
    rows = [
        {
            "case_id": c.case_id,
            "title": c.title,
            "status": c.status,
            "priority": c.priority,
            "source_platform": c.source_platform,
            "source_url": c.source_url or "",
            "analyst": c.analyst or "",
            "assignee": c.assignee.username if c.assignee else "",
            "created_by": c.created_by.username if c.created_by else "",
            "tags": ", ".join(c.tags or []),
            "actors": ", ".join(sorted(link.actor.name for link in c.actor_links)),
            "interactions": len(c.interactions),
            "last_interaction_at": max((i.occurred_at for i in c.interactions), default=""),
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in cases
    ]
    return _csv(rows, fields, "trackactor-cases.csv")


@router.get("/interactions.csv")
def interactions_csv(db: Session = Depends(get_db)):
    fields = ["occurred_at", "case_id", "direction", "summary", "channel", "analyst"]
    rows = db.scalars(
        select(models.Interaction).options(
            selectinload(models.Interaction.contact),
            selectinload(models.Interaction.case),
        ).order_by(models.Interaction.occurred_at)
    ).all()
    return _csv(
        [
            {
                "occurred_at": i.occurred_at,
                "case_id": i.case.case_id if i.case else "",
                "direction": i.direction,
                "summary": i.summary,
                "channel": i.contact.value if i.contact else "",
                "analyst": i.analyst or "",
            }
            for i in rows
        ],
        fields,
        "trackactor-interactions.csv",
    )
