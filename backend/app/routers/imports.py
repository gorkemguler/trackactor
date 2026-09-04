"""/api/import - pull a case in from MISP, TheHive or a STIX 2.1 bundle."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session, selectinload

from .. import events, importers, models, schemas, services
from ..audit import record
from ..database import get_db
from ..serializers import case_detail

router = APIRouter(prefix="/api/import", tags=["import"])

_DETAIL_OPTS = (
    selectinload(models.Case.actor_links).selectinload(models.CaseActor.actor),
    selectinload(models.Case.contact_links)
    .selectinload(models.CaseContact.contact)
    .selectinload(models.Contact.actor),
    selectinload(models.Case.interactions).selectinload(models.Interaction.contact),
)


@router.get("/platforms", response_model=list[str])
def platforms():
    return sorted(importers.MAPPERS)


@router.post("", response_model=schemas.ImportResult, status_code=201)
def run_import(
    payload: schemas.ImportRequest,
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        plan = importers.build_plan(payload.platform, payload.payload)
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(status_code=422, detail=f"could not parse {payload.platform}: {e}") from None

    case, case_created = services.upsert_case(db, plan.case)
    actors_created = 0
    contacts_created = 0

    actors_by_name: dict[str, models.Actor] = {}
    for spec in plan.actors:
        actor, was_new = services.upsert_actor(db, case, spec)
        actors_by_name[actor.name] = actor
        actors_created += int(was_new)

    for contact_spec, actor_name in plan.contacts:
        actor = actors_by_name.get(actor_name) if actor_name else None
        _, was_new = services.upsert_contact(db, case, contact_spec, actor)
        contacts_created += int(was_new)

    record(
        db, request, action="create" if case_created else "update",
        entity_type="case", entity_id=case.id,
        summary=f"imported from {payload.platform}",
    )
    db.commit()

    case = db.get(models.Case, case.id, options=list(_DETAIL_OPTS))
    if case_created:
        events.emit(background, "case.created", events.payload(case))

    return schemas.ImportResult(
        case=case_detail(case),
        case_created=case_created,
        actors_created=actors_created,
        contacts_created=contacts_created,
        notes=plan.notes,
    )
