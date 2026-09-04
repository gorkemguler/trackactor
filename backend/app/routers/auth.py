"""/api/auth - session login for the web UI."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..security import SESSION_COOKIE, create_session, current_user, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
    )


@router.post("/login", response_model=schemas.UserOut)
def login(payload: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.username == payload.username))
    if user is None or user.disabled or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    session = create_session(db, user)
    _set_cookie(response, session.token)
    return schemas.UserOut.model_validate(user)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    trackactor_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if trackactor_session:
        s = db.get(models.Session, trackactor_session)
        if s is not None:
            db.delete(s)
            db.commit()
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User | None = Depends(current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Not logged in")
    return schemas.UserOut.model_validate(user)
