"""API key generation, the request auth gate, and the admin guard."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

KEY_PREFIX = "tk_"
# paths served without a key even when require_key is on
_OPEN_PATHS = {
    "/api/health",
    "/api/meta/enums",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}


def generate_key() -> tuple[str, str, str]:
    """Return (full_key, prefix, sha256_hash). The full key is shown once."""
    body = secrets.token_urlsafe(32)
    full = f"{KEY_PREFIX}{body}"
    return full, full[:12], hashlib.sha256(full.encode()).hexdigest()


def hash_key(full: str) -> str:
    return hashlib.sha256(full.encode()).hexdigest()


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _needs_write(method: str) -> bool:
    return method.upper() not in {"GET", "HEAD", "OPTIONS"}


def auth_gate(
    request: Request,
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    """Global dependency. No-op unless TRACKACTOR_REQUIRE_KEY is set."""
    if not settings.require_key:
        return

    path = request.url.path
    if path in _OPEN_PATHS or path.startswith("/api/docs"):
        return
    # management routes have their own admin guard
    if path.startswith("/api/keys") or path.startswith("/api/webhooks"):
        return

    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header required")

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


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Guards the key / webhook management routes."""
    if not settings.admin_token:
        return  # open on a local instance
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="X-Admin-Token required")
