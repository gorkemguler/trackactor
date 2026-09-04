"""STIX 2.1 bundle -> ImportPlan. Handles the objects OpenCTI and MISP export:
incident / report / grouping for the case, threat-actor / intrusion-set for
actors, and user-account / email-addr / url observables for contacts."""

from __future__ import annotations

from .. import schemas
from .plan import ImportPlan

_CASE_TYPES = ("x-opencti-case-incident", "incident", "report", "grouping", "note")
_ACTOR_TYPES = ("threat-actor", "intrusion-set")


def _channel_for_account(acc: dict) -> tuple[str, str] | None:
    login = acc.get("account_login") or acc.get("display_name")
    if not login:
        return None
    provider = (acc.get("account_type") or "").lower()
    if "telegram" in provider:
        return "telegram", login
    if "discord" in provider:
        return "discord", login
    return "other", login


def plan(payload: dict) -> ImportPlan:
    objects = payload.get("objects") or []
    by_type: dict[str, list[dict]] = {}
    for obj in objects:
        by_type.setdefault(obj.get("type", ""), []).append(obj)

    notes: list[str] = []

    case_obj = next((o for t in _CASE_TYPES for o in by_type.get(t, [])), None)
    if case_obj is None:
        raise ValueError("no incident / report / grouping object in the bundle")

    ext = case_obj.get("external_references") or []
    ext_id = next((e.get("external_id") for e in ext if e.get("external_id")), None)
    ext_url = next((e.get("url") for e in ext if e.get("url")), None)
    case = schemas.CaptureCase(
        case_id=ext_id or case_obj["id"],
        title=case_obj.get("name") or case_obj.get("id"),
        source_platform="STIX",
        source_url=ext_url,
    )

    actors = []
    for t in _ACTOR_TYPES:
        for o in by_type.get(t, []):
            actors.append(
                schemas.CaptureActor(
                    name=o.get("name") or o["id"],
                    actor_type="group" if t == "intrusion-set" else "individual",
                    aliases=o.get("aliases") or [],
                )
            )
    primary = actors[0].name if len(actors) == 1 else None
    if len(actors) > 1:
        notes.append(f"{len(actors)} actors in the bundle; contacts left unattributed")

    contacts: list[tuple[schemas.CaptureContact, str | None]] = []
    for acc in by_type.get("user-account", []):
        got = _channel_for_account(acc)
        if got:
            contacts.append((schemas.CaptureContact(channel_type=got[0], value=got[1]), primary))
    for m in by_type.get("email-addr", []):
        if m.get("value"):
            contacts.append(
                (schemas.CaptureContact(channel_type="email", value=m["value"]), primary)
            )
    for u in by_type.get("url", []):
        if u.get("value"):
            contacts.append(
                (schemas.CaptureContact(channel_type="url", value=u["value"]), primary)
            )

    if not contacts:
        notes.append("no user-account / email-addr / url observables to map to contacts")

    return ImportPlan(case=case, actors=actors, contacts=contacts, notes=notes)
