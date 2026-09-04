"""/api/cases — tracked engagements keyed by an external case ID."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import events, models, schemas
from ..activity import touch_seen
from ..audit import diff, record
from ..database import get_db
from ..normalize import normalize_identifier
from ..security import current_user
from ..serializers import case_detail, case_out, interaction_out

router = APIRouter(prefix="/api/cases", tags=["cases"])

_DETAIL_OPTS = (
    selectinload(models.Case.actor_links).selectinload(models.CaseActor.actor),
    selectinload(models.Case.contact_links)
    .selectinload(models.CaseContact.contact)
    .selectinload(models.Contact.actor),
    selectinload(models.Case.interactions).selectinload(models.Interaction.contact),
    selectinload(models.Case.assignee),
    selectinload(models.Case.created_by),
)


def _load(db: Session, case_id: int) -> models.Case:
    case = db.get(models.Case, case_id, options=list(_DETAIL_OPTS))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("", response_model=schemas.Page[schemas.CaseOut])
def list_cases(
    status: str | None = None,
    priority: str | None = None,
    q: str | None = Query(default=None, description="substring on case_id / title / analyst"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(models.Case)
    if status:
        stmt = stmt.where(models.Case.status == status)
    if priority:
        stmt = stmt.where(models.Case.priority == priority)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            models.Case.case_id.ilike(like)
            | models.Case.title.ilike(like)
            | models.Case.analyst.ilike(like)
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    page = (
        stmt.options(
            selectinload(models.Case.actor_links),
            selectinload(models.Case.interactions),
            selectinload(models.Case.assignee),
            selectinload(models.Case.created_by),
        )
        .order_by(models.Case.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [case_out(c) for c in db.scalars(page).unique().all()]
    return schemas.Page(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=schemas.CaseDetail, status_code=201)
def create_case(
    payload: schemas.CaseCreate,
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User | None = Depends(current_user),
):
    if db.scalar(select(models.Case).where(models.Case.case_id == payload.case_id)):
        raise HTTPException(status_code=409, detail="case_id already exists")

    case = models.Case(
        case_id=payload.case_id,
        title=payload.title,
        source_platform=payload.source_platform,
        source_url=payload.source_url,
        status=payload.status,
        priority=payload.priority,
        analyst=payload.analyst,
        objective=payload.objective,
        tags=payload.tags,
        created_by_id=user.id if user else None,
    )
    for actor_id in dict.fromkeys(payload.actor_ids):
        if db.get(models.Actor, actor_id) is None:
            raise HTTPException(status_code=404, detail=f"actor_id {actor_id} not found")
        case.actor_links.append(models.CaseActor(actor_id=actor_id))
    for contact_id in dict.fromkeys(payload.contact_ids):
        if db.get(models.Contact, contact_id) is None:
            raise HTTPException(status_code=404, detail=f"contact_id {contact_id} not found")
        case.contact_links.append(models.CaseContact(contact_id=contact_id))

    db.add(case)
    db.flush()
    record(db, request, action="create", entity_type="case", entity_id=case.id, summary=case.case_id)
    db.commit()
    loaded = _load(db, case.id)
    events.emit(background, "case.created", events.payload(loaded))
    return case_detail(loaded)


@router.get("/{case_id}", response_model=schemas.CaseDetail)
def get_case(case_id: int, db: Session = Depends(get_db)):
    return case_detail(_load(db, case_id))


@router.get("/{case_id}/export")
def export_case(case_id: int, response: Response, db: Session = Depends(get_db)):
    """A self-contained JSON bundle: the case, its actors and contacts in full,
    the message log, and the audit trail. For handoff."""
    case = _load(db, case_id)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{case.case_id}.trackactor.json"'
    )
    detail = case_detail(case).model_dump(mode="json")
    actor_ids = [link.actor_id for link in case.actor_links]
    actors = db.scalars(
        select(models.Actor)
        .options(selectinload(models.Actor.contacts))
        .where(models.Actor.id.in_(actor_ids))
    ).all() if actor_ids else []
    events = db.scalars(
        select(models.AuditEvent)
        .where(models.AuditEvent.entity_type == "case", models.AuditEvent.entity_id == case_id)
        .order_by(models.AuditEvent.at)
    ).all()
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "case": detail,
        "actors": [
            schemas.ActorDetail(
                **schemas.ActorOut.model_validate(a).model_dump(),
                contacts=[schemas.ContactOut.model_validate(c) for c in a.contacts],
            ).model_dump(mode="json")
            for a in actors
        ],
        "audit": [schemas.AuditEventOut.model_validate(e).model_dump(mode="json") for e in events],
    }


@router.patch("/{case_id}", response_model=schemas.CaseDetail)
def update_case(
    case_id: int,
    payload: schemas.CaseUpdate,
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    case = _load(db, case_id)
    status_before = case.status
    data = payload.model_dump(exclude_unset=True)
    if "case_id" in data and data["case_id"] != case.case_id:
        if db.scalar(select(models.Case).where(models.Case.case_id == data["case_id"])):
            raise HTTPException(status_code=409, detail="case_id already exists")
    if "assignee_id" in data and data["assignee_id"] is not None:
        if db.get(models.User, data["assignee_id"]) is None:
            raise HTTPException(status_code=404, detail="assignee_id not found")
    before = {k: getattr(case, k) for k in data}
    for key, value in data.items():
        setattr(case, key, value)
    changes = diff(before, data)
    if changes:
        record(
            db, request, action="update", entity_type="case", entity_id=case.id,
            summary=", ".join(changes), changes=changes,
        )
    db.commit()
    if case.status != status_before:
        events.emit(background, "case.status_changed", events.payload(_load(db, case_id)))
    return case_detail(_load(db, case_id))


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: int, request: Request, db: Session = Depends(get_db)):
    case = db.get(models.Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    record(db, request, action="delete", entity_type="case", entity_id=case.id, summary=case.case_id)
    db.delete(case)
    db.commit()


# --- linking actors / contacts --------------------------------------


@router.post("/{case_id}/links", response_model=schemas.CaseDetail, status_code=201)
def add_link(
    case_id: int,
    payload: schemas.CaseLinkRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    case = _load(db, case_id)
    if payload.actor_id is None and payload.contact_id is None:
        raise HTTPException(status_code=422, detail="actor_id or contact_id is required")

    if payload.actor_id is not None:
        if db.get(models.Actor, payload.actor_id) is None:
            raise HTTPException(status_code=404, detail="actor_id not found")
        if not any(l.actor_id == payload.actor_id for l in case.actor_links):
            case.actor_links.append(
                models.CaseActor(actor_id=payload.actor_id, note=payload.note)
            )

    if payload.contact_id is not None:
        if db.get(models.Contact, payload.contact_id) is None:
            raise HTTPException(status_code=404, detail="contact_id not found")
        if not any(l.contact_id == payload.contact_id for l in case.contact_links):
            case.contact_links.append(
                models.CaseContact(
                    contact_id=payload.contact_id,
                    outreach_handle=payload.outreach_handle,
                    note=payload.note,
                )
            )

    parts = []
    if payload.actor_id is not None:
        parts.append(f"actor {payload.actor_id}")
    if payload.contact_id is not None:
        parts.append(f"contact {payload.contact_id}")
    record(
        db, request, action="update", entity_type="case", entity_id=case.id,
        summary=f"linked {' + '.join(parts)}",
    )
    db.commit()
    return case_detail(_load(db, case_id))


@router.delete("/{case_id}/links/actor/{actor_id}", response_model=schemas.CaseDetail)
def remove_actor_link(case_id: int, actor_id: int, request: Request, db: Session = Depends(get_db)):
    case = _load(db, case_id)
    for link in list(case.actor_links):
        if link.actor_id == actor_id:
            db.delete(link)
    record(
        db, request, action="update", entity_type="case", entity_id=case.id,
        summary=f"unlinked actor {actor_id}",
    )
    db.commit()
    return case_detail(_load(db, case_id))


@router.delete("/{case_id}/links/contact/{contact_id}", response_model=schemas.CaseDetail)
def remove_contact_link(
    case_id: int, contact_id: int, request: Request, db: Session = Depends(get_db)
):
    case = _load(db, case_id)
    for link in list(case.contact_links):
        if link.contact_id == contact_id:
            db.delete(link)
    record(
        db, request, action="update", entity_type="case", entity_id=case.id,
        summary=f"unlinked contact {contact_id}",
    )
    db.commit()
    return case_detail(_load(db, case_id))


@router.post("/{case_id}/contacts", response_model=schemas.CaseDetail, status_code=201)
def add_case_contact(
    case_id: int,
    payload: schemas.CaseContactCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a channel and link it to the case in one step."""
    case = _load(db, case_id)
    if payload.actor_id is not None and db.get(models.Actor, payload.actor_id) is None:
        raise HTTPException(status_code=404, detail="actor_id not found")

    norm = normalize_identifier(payload.value)
    stmt = select(models.Contact).where(models.Contact.normalized == norm)
    stmt = stmt.where(
        models.Contact.actor_id == payload.actor_id
        if payload.actor_id is not None
        else models.Contact.actor_id.is_(None)
    )
    contact = db.scalar(stmt)
    if contact is None:
        contact = models.Contact(
            actor_id=payload.actor_id,
            channel_type=payload.channel_type,
            value=payload.value,
            normalized=norm,
            label=payload.label,
        )
        db.add(contact)
        db.flush()
    elif payload.actor_id is not None and contact.actor_id is None:
        contact.actor_id = payload.actor_id

    if not any(l.contact_id == contact.id for l in case.contact_links):
        case.contact_links.append(
            models.CaseContact(contact_id=contact.id, outreach_handle=payload.outreach_handle)
        )
    record(
        db, request, action="update", entity_type="case", entity_id=case.id,
        summary=f"added contact {payload.value}",
    )
    db.commit()
    return case_detail(_load(db, case_id))


# --- interactions ----------------------------------------------------


@router.get("/{case_id}/interactions", response_model=list[schemas.InteractionOut])
def list_interactions(case_id: int, db: Session = Depends(get_db)):
    case = _load(db, case_id)
    return [interaction_out(i) for i in case.interactions]


@router.post(
    "/{case_id}/interactions", response_model=schemas.InteractionOut, status_code=201
)
def add_interaction(
    case_id: int,
    payload: schemas.InteractionCreate,
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    case = db.get(models.Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    contact = None
    if payload.contact_id is not None:
        contact = db.get(models.Contact, payload.contact_id)
        if contact is None:
            raise HTTPException(status_code=404, detail="contact_id not found")

    interaction = models.Interaction(
        case_id=case_id,
        contact_id=payload.contact_id,
        direction=payload.direction,
        occurred_at=payload.occurred_at or datetime.now(timezone.utc),
        summary=payload.summary,
        analyst=payload.analyst,
    )
    db.add(interaction)
    if contact is not None:
        touch_seen(contact=contact)

    status_changed = payload.direction == "inbound" and case.status == "awaiting_response"
    if status_changed:
        case.status = "responded"

    db.flush()
    record(
        db, request, action="update", entity_type="case", entity_id=case.id,
        summary=f"logged {interaction.direction} message",
    )
    db.commit()
    db.refresh(interaction)

    events.emit(
        background, f"interaction.{interaction.direction}", events.payload(case, interaction)
    )
    if status_changed:
        events.emit(background, "case.status_changed", events.payload(case))
    return interaction_out(interaction)


@router.patch(
    "/{case_id}/interactions/{interaction_id}", response_model=schemas.InteractionOut
)
def update_interaction(
    case_id: int,
    interaction_id: int,
    payload: schemas.InteractionUpdate,
    db: Session = Depends(get_db),
):
    interaction = db.get(models.Interaction, interaction_id)
    if interaction is None or interaction.case_id != case_id:
        raise HTTPException(status_code=404, detail="Interaction not found")
    data = payload.model_dump(exclude_unset=True)
    if "contact_id" in data and data["contact_id"] is not None:
        if db.get(models.Contact, data["contact_id"]) is None:
            raise HTTPException(status_code=404, detail="contact_id not found")
    for key, value in data.items():
        setattr(interaction, key, value)
    db.commit()
    db.refresh(interaction)
    return interaction_out(interaction)


@router.delete("/{case_id}/interactions/{interaction_id}", status_code=204)
def delete_interaction(
    case_id: int, interaction_id: int, request: Request, db: Session = Depends(get_db)
):
    interaction = db.get(models.Interaction, interaction_id)
    if interaction is None or interaction.case_id != case_id:
        raise HTTPException(status_code=404, detail="Interaction not found")
    record(
        db, request, action="update", entity_type="case", entity_id=case_id,
        summary=f"deleted {interaction.direction} message",
    )
    db.delete(interaction)
    db.commit()
