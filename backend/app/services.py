"""Shared upsert logic behind /api/capture and /api/import."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .normalize import normalize_identifier


def upsert_case(db: Session, spec: schemas.CaptureCase) -> tuple[models.Case, bool]:
    case = db.scalar(select(models.Case).where(models.Case.case_id == spec.case_id))
    if case is not None:
        if spec.source_url and not case.source_url:
            case.source_url = spec.source_url
        return case, False
    case = models.Case(
        case_id=spec.case_id,
        title=spec.title or spec.case_id,
        source_platform=spec.source_platform or "Manual",
        source_url=spec.source_url,
        status=spec.status or "open",
        priority=spec.priority or "medium",
        analyst=spec.analyst,
        objective=spec.objective,
    )
    db.add(case)
    db.flush()
    return case, True


def upsert_actor(
    db: Session, case: models.Case, spec: schemas.CaptureActor
) -> tuple[models.Actor, bool]:
    actor = db.scalar(select(models.Actor).where(models.Actor.name == spec.name))
    created = actor is None
    if created:
        actor = models.Actor(
            name=spec.name, actor_type=spec.actor_type, aliases=spec.aliases
        )
        db.add(actor)
        db.flush()
    if not any(link.actor_id == actor.id for link in case.actor_links):
        db.add(models.CaseActor(case_id=case.id, actor_id=actor.id))
    return actor, created


def upsert_contact(
    db: Session,
    case: models.Case,
    spec: schemas.CaptureContact,
    actor: models.Actor | None,
) -> tuple[models.Contact, bool]:
    norm = normalize_identifier(spec.value)
    stmt = select(models.Contact).where(models.Contact.normalized == norm)
    stmt = stmt.where(
        models.Contact.actor_id == actor.id
        if actor is not None
        else models.Contact.actor_id.is_(None)
    )
    contact = db.scalar(stmt)
    created = contact is None
    if created:
        contact = models.Contact(
            actor_id=actor.id if actor else None,
            channel_type=spec.channel_type,
            value=spec.value,
            normalized=norm,
            label=spec.label,
        )
        db.add(contact)
        db.flush()
    elif actor is not None and contact.actor_id is None:
        contact.actor_id = actor.id
    if not any(link.contact_id == contact.id for link in case.contact_links):
        db.add(models.CaseContact(case_id=case.id, contact_id=contact.id))
    return contact, created


def add_interaction(
    db: Session,
    case: models.Case,
    contact: models.Contact | None,
    spec: schemas.CaptureInteraction,
    default_analyst: str | None = None,
) -> tuple[models.Interaction, bool]:
    """Returns (interaction, status_flipped_to_responded)."""
    interaction = models.Interaction(
        case_id=case.id,
        contact_id=contact.id if contact else None,
        direction=spec.direction,
        occurred_at=spec.occurred_at or datetime.now(timezone.utc),
        summary=spec.summary,
        analyst=spec.analyst or default_analyst,
    )
    db.add(interaction)
    flipped = spec.direction == "inbound" and case.status == "awaiting_response"
    if flipped:
        case.status = "responded"
    return interaction, flipped
