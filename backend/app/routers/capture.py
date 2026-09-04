"""/api/capture - one request that upserts a case, an actor, a contact and an
optional message, and wires the links between them. Built for the browser
extension: grab a case id from a CTI platform, grab a handle from a chat, done."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session, selectinload

from .. import events, models, schemas, services
from ..activity import touch_seen
from ..database import get_db
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
def capture(
    payload: schemas.CapturePayload,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    created = {"case": False, "actor": False, "contact": False, "interaction": False}
    status_changed = False

    case, created["case"] = services.upsert_case(db, payload.case)

    actor = None
    if payload.actor:
        actor, created["actor"] = services.upsert_actor(db, case, payload.actor)

    contact = None
    if payload.contact:
        contact, created["contact"] = services.upsert_contact(db, case, payload.contact, actor)

    new_interaction = None
    if payload.interaction:
        new_interaction, status_changed = services.add_interaction(
            db, case, contact, payload.interaction, payload.case.analyst
        )
        created["interaction"] = True

    touch_seen(contact=contact, actor=actor)
    db.commit()

    case = db.get(models.Case, case.id, options=list(_DETAIL_OPTS))

    if created["case"]:
        events.emit(background, "case.created", events.payload(case))
    if new_interaction is not None:
        events.emit(
            background,
            f"interaction.{new_interaction.direction}",
            events.payload(case, new_interaction),
        )
    if status_changed:
        events.emit(background, "case.status_changed", events.payload(case))

    return schemas.CaptureResult(case=case_detail(case), created=created)
