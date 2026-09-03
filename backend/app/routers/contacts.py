"""/api/contacts — communication identifiers, listed and searched on their own."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..normalize import normalize_identifier
from ..serializers import contact_with_actor

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", response_model=schemas.Page[schemas.ContactWithActor])
def list_contacts(
    q: str | None = Query(default=None, description="substring match on value / normalized"),
    channel_type: str | None = None,
    unattributed: bool = Query(default=False, description="only contacts with no actor"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(models.Contact)
    if channel_type:
        stmt = stmt.where(models.Contact.channel_type == channel_type)
    if unattributed:
        stmt = stmt.where(models.Contact.actor_id.is_(None))
    if q:
        norm = normalize_identifier(q)
        stmt = stmt.where(
            models.Contact.value.ilike(f"%{q.lower()}%")
            | models.Contact.normalized.ilike(f"%{norm}%")
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    page = (
        stmt.options(selectinload(models.Contact.actor))
        .order_by(models.Contact.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [contact_with_actor(c) for c in db.scalars(page).unique().all()]
    return schemas.Page(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=schemas.ContactWithActor, status_code=201)
def create_contact(payload: schemas.ContactCreate, db: Session = Depends(get_db)):
    if payload.actor_id is not None and db.get(models.Actor, payload.actor_id) is None:
        raise HTTPException(status_code=404, detail="actor_id does not exist")
    contact = models.Contact(
        actor_id=payload.actor_id,
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
    return contact_with_actor(contact)


@router.get("/{contact_id}", response_model=schemas.ContactWithActor)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.get(models.Contact, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact_with_actor(contact)


@router.patch("/{contact_id}", response_model=schemas.ContactWithActor)
def update_contact(
    contact_id: int, payload: schemas.ContactUpdate, db: Session = Depends(get_db)
):
    contact = db.get(models.Contact, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    data = payload.model_dump(exclude_unset=True)
    if "actor_id" in data and data["actor_id"] is not None:
        if db.get(models.Actor, data["actor_id"]) is None:
            raise HTTPException(status_code=404, detail="actor_id does not exist")
    for key, value in data.items():
        setattr(contact, key, value)
    if "value" in data:
        contact.normalized = normalize_identifier(contact.value)
    db.commit()
    db.refresh(contact)
    return contact_with_actor(contact)


@router.delete("/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.get(models.Contact, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
