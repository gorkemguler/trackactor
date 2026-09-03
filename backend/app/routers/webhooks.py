"""/api/webhooks - outbound webhook subscriptions. Same admin guard as /api/keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..events import EVENTS, send_test
from ..security import require_admin

router = APIRouter(
    prefix="/api/webhooks", tags=["webhooks"], dependencies=[Depends(require_admin)]
)


@router.get("/events", response_model=list[str])
def known_events():
    return EVENTS


@router.get("", response_model=list[schemas.WebhookOut])
def list_webhooks(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.Webhook).order_by(models.Webhook.created_at.desc())).all()
    return [schemas.WebhookOut.model_validate(w) for w in rows]


@router.post("", response_model=schemas.WebhookOut, status_code=201)
def create_webhook(payload: schemas.WebhookCreate, db: Session = Depends(get_db)):
    bad = [e for e in payload.events if e != "*" and e not in EVENTS]
    if bad:
        raise HTTPException(status_code=422, detail=f"unknown events: {bad}")
    hook = models.Webhook(
        url=payload.url, secret=payload.secret, events=payload.events, active=payload.active
    )
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return schemas.WebhookOut.model_validate(hook)


@router.patch("/{hook_id}", response_model=schemas.WebhookOut)
def update_webhook(hook_id: int, payload: schemas.WebhookUpdate, db: Session = Depends(get_db)):
    hook = db.get(models.Webhook, hook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    data = payload.model_dump(exclude_unset=True)
    if "events" in data:
        bad = [e for e in data["events"] if e != "*" and e not in EVENTS]
        if bad:
            raise HTTPException(status_code=422, detail=f"unknown events: {bad}")
    for k, v in data.items():
        setattr(hook, k, v)
    db.commit()
    db.refresh(hook)
    return schemas.WebhookOut.model_validate(hook)


@router.delete("/{hook_id}", status_code=204)
def delete_webhook(hook_id: int, db: Session = Depends(get_db)):
    hook = db.get(models.Webhook, hook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(hook)
    db.commit()


@router.post("/{hook_id}/test")
def test_webhook(hook_id: int, db: Session = Depends(get_db)):
    hook = db.get(models.Webhook, hook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return send_test(hook)
