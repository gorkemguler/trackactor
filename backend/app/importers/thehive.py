"""TheHive case JSON -> ImportPlan. Maps the case fields and any mail / other
observables; actor attribution on TheHive is free-form, so that's left to the
analyst."""

from __future__ import annotations

from .. import schemas
from .plan import ImportPlan

_MAIL = {"mail", "email"}


def plan(payload: dict) -> ImportPlan:
    if not payload.get("title"):
        raise ValueError("not a TheHive case (no 'title' field)")

    notes: list[str] = []
    number = payload.get("caseId") or payload.get("number")
    case = schemas.CaptureCase(
        case_id=payload.get("sourceRef") or (f"THEHIVE-{number}" if number else "THEHIVE-case"),
        title=payload["title"],
        source_platform="TheHive",
        objective=payload.get("description"),
        priority={1: "low", 2: "medium", 3: "high", 4: "critical"}.get(payload.get("severity")),
    )

    contacts: list[tuple[schemas.CaptureContact, str | None]] = []
    for obs in payload.get("observables", []) or payload.get("artifacts", []):
        dtype = (obs.get("dataType") or obs.get("type") or "").lower()
        value = obs.get("data") or obs.get("value")
        if not value:
            continue
        if dtype in _MAIL:
            contacts.append((schemas.CaptureContact(channel_type="email", value=value), None))
        elif dtype in {"url", "uri"}:
            contacts.append((schemas.CaptureContact(channel_type="url", value=value), None))
        elif dtype == "other":
            contacts.append((schemas.CaptureContact(channel_type="other", value=value), None))

    notes.append("actors are not mapped from TheHive - add them by hand")
    if not contacts:
        notes.append("no mail / url / other observables to map to contacts")

    return ImportPlan(case=case, actors=[], contacts=contacts, notes=notes)
