"""MISP event JSON -> ImportPlan. Accepts either {"Event": {...}} or a bare
event object."""

from __future__ import annotations

from .. import schemas
from .plan import ImportPlan

_EMAIL_TYPES = {"email", "email-src", "email-dst", "email-reply-to"}
_URL_TYPES = {"link", "url", "uri"}


def plan(payload: dict) -> ImportPlan:
    ev = payload.get("Event", payload)
    if not ev.get("info"):
        raise ValueError("not a MISP event (no 'info' field)")

    notes: list[str] = []
    tags = [t.get("name", "") for t in ev.get("Tag", []) if t.get("name")]
    case = schemas.CaptureCase(
        case_id=ev.get("uuid") or f"MISP-{ev.get('id', 'event')}",
        title=ev["info"],
        source_platform="MISP",
        objective="MISP tags: " + ", ".join(tags) if tags else None,
    )

    actors: list[schemas.CaptureActor] = []
    for galaxy in ev.get("Galaxy", []):
        gtype = (galaxy.get("type") or "").lower()
        if "threat-actor" not in gtype and "intrusion-set" not in gtype:
            continue
        for cluster in galaxy.get("GalaxyCluster", []):
            synonyms = (cluster.get("meta") or {}).get("synonyms") or []
            actors.append(
                schemas.CaptureActor(
                    name=cluster.get("value") or cluster.get("uuid"),
                    actor_type="group",
                    aliases=[s["value"] if isinstance(s, dict) else s for s in synonyms],
                )
            )
    primary = actors[0].name if len(actors) == 1 else None

    contacts: list[tuple[schemas.CaptureContact, str | None]] = []
    for attr in ev.get("Attribute", []):
        atype = (attr.get("type") or "").lower()
        value = attr.get("value")
        if not value:
            continue
        if atype in _EMAIL_TYPES:
            contacts.append((schemas.CaptureContact(channel_type="email", value=value), primary))
        elif atype in _URL_TYPES:
            contacts.append((schemas.CaptureContact(channel_type="url", value=value), primary))

    if not actors:
        notes.append("no threat-actor galaxy cluster on the event")
    if not contacts:
        notes.append("no email / url attributes to map to contacts")

    return ImportPlan(case=case, actors=actors, contacts=contacts, notes=notes)
