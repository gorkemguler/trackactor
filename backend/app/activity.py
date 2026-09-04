"""Keep last_seen fresh whenever we record contact with an actor."""

from __future__ import annotations

from datetime import UTC, datetime

from . import models


def touch_seen(*, contact: models.Contact | None = None, actor: models.Actor | None = None) -> None:
    now = datetime.now(UTC)
    if contact is not None:
        contact.last_seen = now
        if contact.actor is not None:
            contact.actor.last_seen = now
    if actor is not None:
        actor.last_seen = now
