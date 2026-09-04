"""API keys, passwords, sessions, the request auth gate, and the admin guard."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

KEY_PREFIX = "tk_"
SESSION_COOKIE = "trackactor_session"
_PBKDF2_ROUNDS = 240_000

_OPEN_PATHS = {
    "/api/health",
    "/api/meta/enums",
    "/api/meta/config",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}


# --- API keys --------------------------------------------------------


def generate_key() -> tuple[str, str, str]:
    body = secrets.token_urlsafe(32)
    full = f"{KEY_PREFIX}{body}"
    return full, full[:12], hashlib.sha256(full.encode()).hexdigest()


def hash_key(full: str) -> str:
    return hashlib.sha256(full.encode()).hexdigest()


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# --- passwords ----------------------------------------------------


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt, want = stored.split("$")
        got = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(rounds)
        ).hex()
        return hmac.compare_digest(got, want)
    except (ValueError, AttributeError):
        return False


# --- sessions ---------------------------------------------------


def create_session(db: Session, user: models.User) -> models.Session:
    now = datetime.now(timezone.utc)
    s = models.Session(
        token=secrets.token_urlsafe(32),
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(s)
    db.commit()
    return s


def _session_user(db: Session, token: str | None) -> models.User | None:
    if not token:
        return None
    s = db.get(models.Session, token)
    if s is None:
        return None
    if s.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        db.delete(s)
        db.commit()
        return None
    return None if s.user.disabled else s.user


def current_user(
    request: Request,
    trackactor_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> models.User | None:
    """The logged-in user, or None. Also stashed on request.state for the audit log."""
    user = getattr(request.state, "user", None)
    if user is None:
        user = _session_user(db, trackactor_session)
        request.state.user = user
    return user


# --- gates ----------------------------------------------------


def _needs_write(method: str) -> bool:
    return method.upper() not in {"GET", "HEAD", "OPTIONS"}


def auth_gate(
    request: Request,
    x_api_key: str | None = Header(default=None),
    trackactor_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> None:
    """Global dependency. No-op unless a require_* flag is set."""
    if not settings.require_key and not settings.require_login:
        return

    path = request.url.path
    if path in _OPEN_PATHS or path.startswith("/api/docs") or path.startswith("/api/auth"):
        return
    if path.startswith("/api/keys") or path.startswith("/api/webhooks"):
        return  # admin-guarded

    user = _session_user(db, trackactor_session)
    if user is not None:
        request.state.user = user
        return  # a logged-in user may do anything

    if x_api_key:
        key = db.scalar(
            select(models.ApiKey).where(
                models.ApiKey.key_hash == hash_key(x_api_key),
                models.ApiKey.revoked.is_(False),
            )
        )
        if key is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        if _needs_write(request.method) and key.scope != "write":
            raise HTTPException(status_code=403, detail="This key is read-only")
        key.last_used_at = datetime.now(timezone.utc)
        db.commit()
        return

    raise HTTPException(status_code=401, detail="Authentication required")


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not settings.admin_token:
        return
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="X-Admin-Token required")
