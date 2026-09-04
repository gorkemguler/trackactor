"""/api/users - account management. Admin-guarded like /api/keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import hash_password, require_admin

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    """Readable by any authenticated caller - used to populate the assignee picker."""
    rows = db.scalars(select(models.User).order_by(models.User.username)).all()
    return [schemas.UserOut.model_validate(u) for u in rows]


@router.post("", response_model=schemas.UserOut, status_code=201, dependencies=[Depends(require_admin)])
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(models.User).where(models.User.username == payload.username)):
        raise HTTPException(status_code=409, detail="username taken")
    user = models.User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=schemas.UserOut, dependencies=[Depends(require_admin)])
def update_user(
    user_id: int,
    disabled: bool | None = None,
    password: str | None = None,
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if disabled is not None:
        user.disabled = disabled
    if password:
        user.password_hash = hash_password(password)
    db.commit()
    return schemas.UserOut.model_validate(user)
