"""/api/capture - one request that upserts a case, an actor, a contact and an
optional message, and wires the links between them. Built for the browser
extension: grab a case id from a CTI platform, grab a handle from a chat, done."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..activity import touch_seen
from ..database import get_db
from ..normalize import normalize_identifier
from ..serializers import case_detail

router = APIRouter(prefix="/api/capture", tags=["capture"])

_DETAIL_OPTS = (
    selectinload(models.Case.actor_links).selectinload(models.CaseActor.actor),
    selectinload(models.Case.contact_links)
    .selectinload(models.CaseContact.contact)
    .selectinload(models.Contact.actor),
    selectinload(models.Case.interactions).selectinload(models.Interaction.contact),
)


@router.post("", response_model=schemas.CaptureResult, status_code=201)
def capture(payload: schemas.CapturePayload, db: Session = Depends(get_db)):
    created = {"case": False, "actor": False, "contact": False, "interaction": False}

    # --- case ---------------------------------------------------------
    case = db.scalar(select(models.Case).where(models.Case.case_id == payload.case.case_id))
    if case is None:
        case = models.Case(
            case_id=payload.case.case_id,
            title=payload.case.title or payload.case.case_id,
            source_platform=payload.case.source_platform or "Manual",
            source_url=payload.case.source_url,
            status=payload.case.status or "open",
            priority=payload.case.priority or "medium",
            analyst=payload.case.analyst,
        )
        db.add(case)
        db.flush()
        created["case"] = True
    elif payload.case.source_url and not case.source_url:
        case.source_url = payload.case.source_url

    # --- actor -------------------------------------------------------
    actor = None
    if payload.actor:
        actor = db.scalar(select(models.Actor).where(models.Actor.name == payload.actor.name))
        if actor is None:
            actor = models.Actor(
                name=payload.actor.name,
                actor_type=payload.actor.actor_type,
                aliases=payload.actor.aliases,
            )
            db.add(actor)
            db.flush()
            created["actor"] = True
        if not any(link.actor_id == actor.id for link in case.actor_links):
            db.add(models.CaseActor(case_id=case.id, actor_id=actor.id))

    # --- contact ---------------------------------------------------
    contact = None
    if payload.contact:
        norm = normalize_identifier(payload.contact.value)
        stmt = select(models.Contact).where(models.Contact.normalized == norm)
        stmt = stmt.where(
            models.Contact.actor_id == actor.id
            if actor is not None
            else models.Contact.actor_id.is_(None)
        )
        contact = db.scalar(stmt)
        if contact is None:
            contact = models.Contact(
                actor_id=actor.id if actor else None,
                channel_type=payload.contact.channel_type,
                value=payload.contact.value,
                normalized=norm,
                label=payload.contact.label,
            )
            db.add(contact)
            db.flush()
            created["contact"] = True
        elif actor is not None and contact.actor_id is None:
            contact.actor_id = actor.id
        if not any(link.contact_id == contact.id for link in case.contact_links):
            db.add(models.CaseContact(case_id=case.id, contact_id=contact.id))

    # --- message --------------------------------------------------
    if payload.interaction:
        db.add(
            models.Interaction(
                case_id=case.id,
                contact_id=contact.id if contact else None,
                direction=payload.interaction.direction,
                occurred_at=payload.interaction.occurred_at or datetime.now(timezone.utc),
                summary=payload.interaction.summary,
                analyst=payload.interaction.analyst or payload.case.analyst,
            )
        )
        created["interaction"] = True
        if payload.interaction.direction == "inbound" and case.status == "awaiting_response":
            case.status = "responded"

    touch_seen(contact=contact, actor=actor)

    db.commit()

    case = db.get(models.Case, case.id, options=list(_DETAIL_OPTS))
    return schemas.CaptureResult(case=case_detail(case), created=created)
