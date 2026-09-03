"""Outbound webhooks. Delivery runs in a background task so it never blocks or
fails the request that triggered it."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import httpx
from fastapi import BackgroundTasks
from sqlalchemy import select

from . import models
from .database import SessionLocal
from .security import sign

EVENTS = [
    "interaction.inbound",
    "interaction.outbound",
    "case.status_changed",
    "case.created",
]

_RETRY_DELAYS = (0.0, 1.0, 3.0)  # 3 attempts


def emit(background: BackgroundTasks, event: str, data: dict) -> None:
    """Queue a webhook fan-out for after the response is sent."""
    background.add_task(_deliver, event, data)


def payload(case, interaction=None) -> dict:
    data = {
        "case": {
            "id": case.id,
            "case_id": case.case_id,
            "title": case.title,
            "status": case.status,
            "priority": case.priority,
            "source_platform": case.source_platform,
        }
    }
    if interaction is not None:
        data["interaction"] = {
            "id": interaction.id,
            "direction": interaction.direction,
            "summary": interaction.summary,
            "occurred_at": interaction.occurred_at.isoformat(),
            "contact": interaction.contact.value if interaction.contact else None,
        }
    return data


def _subscribers(db, event: str) -> list[models.Webhook]:
    hooks = db.scalars(select(models.Webhook).where(models.Webhook.active.is_(True))).all()
    return [h for h in hooks if "*" in (h.events or []) or event in (h.events or [])]


def _post(hook: models.Webhook, body: bytes) -> int:
    last_exc = None
    for delay in _RETRY_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            res = httpx.post(
                hook.url,
                content=body,
                headers={
                    "content-type": "application/json",
                    "user-agent": "trackactor-webhook/1",
                    "x-trackactor-signature": sign(hook.secret, body),
                },
                timeout=5.0,
            )
            if res.status_code < 500:
                return res.status_code
            last_exc = f"HTTP {res.status_code}"
        except httpx.HTTPError as e:
            last_exc = str(e)
    raise RuntimeError(last_exc or "delivery failed")


def _deliver(event: str, data: dict) -> None:
    body = json.dumps(
        {"event": event, "at": datetime.now(timezone.utc).isoformat(), "data": data},
        default=str,
    ).encode()

    db = SessionLocal()
    try:
        for hook in _subscribers(db, event):
            hook.last_attempt_at = datetime.now(timezone.utc)
            try:
                hook.last_status = _post(hook, body)
                hook.failure_count = 0
            except Exception:
                hook.last_status = None
                hook.failure_count += 1
            db.commit()
    finally:
        db.close()


def send_test(hook: models.Webhook) -> dict:
    """Synchronous single POST for the 'test' button."""
    body = json.dumps(
        {"event": "ping", "at": datetime.now(timezone.utc).isoformat(), "data": {"hook_id": hook.id}},
        default=str,
    ).encode()
    try:
        status = _post(hook, body)
        ok = status < 400
        return {"ok": ok, "status": status}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "status": None, "error": str(e)}
