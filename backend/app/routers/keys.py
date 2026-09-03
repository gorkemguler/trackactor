"""/api/keys - manage API keys. Guarded by X-Admin-Token when one is configured."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import generate_key, require_admin

router = APIRouter(prefix="/api/keys", tags=["keys"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[schemas.ApiKeyOut])
def list_keys(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.ApiKey).order_by(models.ApiKey.created_at.desc())).all()
    return [schemas.ApiKeyOut.model_validate(k) for k in rows]


@router.post("", response_model=schemas.ApiKeyCreated, status_code=201)
def create_key(payload: schemas.ApiKeyCreate, db: Session = Depends(get_db)):
    if payload.scope not in ("read", "write"):
        raise HTTPException(status_code=422, detail="scope must be 'read' or 'write'")
    full, prefix, key_hash = generate_key()
    key = models.ApiKey(
        label=payload.label, prefix=prefix, key_hash=key_hash, scope=payload.scope
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return schemas.ApiKeyCreated(**schemas.ApiKeyOut.model_validate(key).model_dump(), key=full)


@router.delete("/{key_id}", status_code=204)
def revoke_key(key_id: int, db: Session = Depends(get_db)):
    key = db.get(models.ApiKey, key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="Key not found")
    key.revoked = True
    db.commit()
