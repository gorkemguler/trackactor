"""/api/actors — threat actors and their aliases."""

from __future__ import annotations

from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..audit import diff, record
from ..database import get_db
from ..normalize import normalize_identifier, normalize_name
from ..serializers import actor_detail, contact_out

router = APIRouter(prefix="/api/actors", tags=["actors"])


def _get_actor(db: Session, actor_id: int) -> models.Actor:
    actor = db.get(
        models.Actor,
        actor_id,
        options=[selectinload(models.Actor.contacts), selectinload(models.Actor.case_links).selectinload(models.CaseActor.case)],
    )
    if actor is None:
        raise HTTPException(status_code=404, detail="Actor not found")
    return actor


@router.get("/similar", response_model=list[schemas.ActorOut])
def similar_actors(name: str = Query(min_length=1), db: Session = Depends(get_db)):
    """Advisory near-duplicate check for the new-actor form."""
    q = normalize_name(name)
    out: list[tuple[float, models.Actor]] = []
    for a in db.scalars(select(models.Actor)):
        names = [normalize_name(a.name), *(normalize_name(x) for x in (a.aliases or []))]
        best = max(
            (
                1.0
                if q == n
                else 0.9
                if n and (q in n or n in q)
                else SequenceMatcher(None, q, n).ratio()
                for n in names
                if n
            ),
            default=0.0,
        )
        if best >= 0.7:
            out.append((best, a))
    out.sort(key=lambda t: t[0], reverse=True)
    return [schemas.ActorOut.model_validate(a) for _, a in out[:5]]


@router.get("", response_model=schemas.Page[schemas.ActorDetail])
def list_actors(
    q: str | None = Query(default=None, description="filter by name / alias substring"),
    actor_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(models.Actor).options(
        selectinload(models.Actor.contacts),
        selectinload(models.Actor.case_links).selectinload(models.CaseActor.case),
    )
    if actor_type:
        stmt = stmt.where(models.Actor.actor_type == actor_type)
    actors = db.scalars(stmt.order_by(models.Actor.name)).unique().all()

    # aliases live in a JSON column, so filter name/alias in Python
    if q:
        ql = q.lower()
        actors = [
            a
            for a in actors
            if ql in a.name.lower()
            or any(ql in (al or "").lower() for al in (a.aliases or []))
        ]

    page = actors[offset : offset + limit]
    return schemas.Page(
        items=[actor_detail(a) for a in page],
        total=len(actors),
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=schemas.ActorDetail, status_code=201)
def create_actor(
    payload: schemas.ActorCreate, request: Request, db: Session = Depends(get_db)
):
    if db.scalar(select(models.Actor).where(models.Actor.name == payload.name)):
        raise HTTPException(status_code=409, detail="An actor with that name already exists")

    actor = models.Actor(
        name=payload.name,
        actor_type=payload.actor_type,
        aliases=payload.aliases,
        description=payload.description,
        tlp=payload.tlp,
        first_seen=payload.first_seen,
        last_seen=payload.last_seen,
    )
    for c in payload.contacts:
        actor.contacts.append(
            models.Contact(
                channel_type=c.channel_type,
                value=c.value,
                normalized=normalize_identifier(c.value),
                label=c.label,
                is_active=c.is_active,
                notes=c.notes,
            )
        )
    db.add(actor)
    db.flush()
    record(
        db, request, action="create", entity_type="actor", entity_id=actor.id,
        summary=actor.name,
    )
    db.commit()
    db.refresh(actor)
    return actor_detail(_get_actor(db, actor.id))


@router.get("/{actor_id}", response_model=schemas.ActorDetail)
def get_actor(actor_id: int, db: Session = Depends(get_db)):
    return actor_detail(_get_actor(db, actor_id))


@router.patch("/{actor_id}", response_model=schemas.ActorDetail)
def update_actor(
    actor_id: int, payload: schemas.ActorUpdate, request: Request, db: Session = Depends(get_db)
):
    actor = _get_actor(db, actor_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != actor.name:
        if db.scalar(select(models.Actor).where(models.Actor.name == data["name"])):
            raise HTTPException(status_code=409, detail="An actor with that name already exists")
    before = {k: getattr(actor, k) for k in data}
    for key, value in data.items():
        setattr(actor, key, value)
    changes = diff(before, data)
    if changes:
        record(
            db, request, action="update", entity_type="actor", entity_id=actor.id,
            summary=", ".join(changes), changes=changes,
        )
    db.commit()
    return actor_detail(_get_actor(db, actor_id))


@router.delete("/{actor_id}", status_code=204)
def delete_actor(actor_id: int, request: Request, db: Session = Depends(get_db)):
    actor = db.get(models.Actor, actor_id)
    if actor is None:
        raise HTTPException(status_code=404, detail="Actor not found")
    record(
        db, request, action="delete", entity_type="actor", entity_id=actor.id,
        summary=actor.name,
    )
    db.delete(actor)
    db.commit()


# --- nested contacts ---------------------------------------------------


@router.post("/{actor_id}/contacts", response_model=schemas.ContactOut, status_code=201)
def add_contact(actor_id: int, payload: schemas.ContactBase, db: Session = Depends(get_db)):
    actor = db.get(models.Actor, actor_id)
    if actor is None:
        raise HTTPException(status_code=404, detail="Actor not found")
    contact = models.Contact(
        actor_id=actor_id,
        channel_type=payload.channel_type,
        value=payload.value,
        normalized=normalize_identifier(payload.value),
        label=payload.label,
        is_active=payload.is_active,
        notes=payload.notes,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact_out(contact)
