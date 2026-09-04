"""/api/lookup — resolve an inbound handle / link / alias / case id to the
case(s) it belongs to, going through the matching contact or actor."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..database import get_db
from ..normalize import normalize_identifier, normalize_name

router = APIRouter(prefix="/api/lookup", tags=["lookup"])


def _last_interaction_at(case: models.Case):
    return max((i.occurred_at for i in case.interactions), default=None)


def _case_hit(case: models.Case, via: str) -> schemas.LookupCaseHit:
    return schemas.LookupCaseHit(
        id=case.id,
        case_id=case.case_id,
        title=case.title,
        status=case.status,
        priority=case.priority,
        source_platform=case.source_platform,
        analyst=case.analyst,
        last_interaction_at=_last_interaction_at(case),
        via=via,
    )


def _cases_for_actor(actor: models.Actor) -> list[models.Case]:
    return [link.case for link in actor.case_links]


def _cases_for_contact(contact: models.Contact) -> list[models.Case]:
    cases = {link.case.id: link.case for link in contact.case_links}
    if contact.actor:
        for link in contact.actor.case_links:
            cases.setdefault(link.case.id, link.case)
    return list(cases.values())


@router.get("", response_model=schemas.LookupResponse)
def lookup(
    q: str = Query(min_length=1, description="handle, link, alias or case id"),
    db: Session = Depends(get_db),
):
    norm = normalize_identifier(q)
    name_norm = normalize_name(q)
    raw_lower = q.strip().lower()

    contact_opts = [
        selectinload(models.Contact.actor).selectinload(models.Actor.case_links).selectinload(models.CaseActor.case).selectinload(models.Case.interactions),
        selectinload(models.Contact.case_links).selectinload(models.CaseContact.case).selectinload(models.Case.interactions),
    ]

    # --- contacts -----------------------------------------------------
    # Match on the indexed `normalized` column instead of scanning every row:
    # exact hit uses the index; the substring / raw-value clauses narrow the
    # rest in the database rather than in Python.
    conds = []
    if norm:
        conds.append(models.Contact.normalized == norm)
        conds.append(models.Contact.normalized.like(f"%{norm}%"))
    if raw_lower:
        conds.append(func.lower(models.Contact.value).like(f"%{raw_lower}%"))

    contact_hits: list[schemas.LookupContactHit] = []
    matched = (
        db.scalars(select(models.Contact).options(*contact_opts).where(or_(*conds))).unique().all()
        if conds
        else []
    )
    for c in matched:
        cn = c.normalized or ""
        norm_partial = bool(norm) and norm in cn
        raw_partial = bool(raw_lower) and raw_lower in c.value.lower()
        if norm and cn == norm:
            match = "exact"
        elif norm_partial or raw_partial:
            match = "partial"
        else:
            continue
        contact_hits.append(
            schemas.LookupContactHit(
                id=c.id,
                channel_type=c.channel_type,
                value=c.value,
                normalized=c.normalized,
                label=c.label,
                is_active=c.is_active,
                actor_id=c.actor_id,
                actor_name=c.actor.name if c.actor else None,
                match=match,
                cases=[_case_hit(case, "contact") for case in _cases_for_contact(c)],
            )
        )

    # --- actors --------------------------------------------------------
    actor_opts = [
        selectinload(models.Actor.case_links).selectinload(models.CaseActor.case).selectinload(models.Case.interactions)
    ]
    all_actors = db.scalars(select(models.Actor).options(*actor_opts)).unique().all()
    actor_hits: list[schemas.LookupActorHit] = []
    for a in all_actors:
        names = [normalize_name(a.name)] + [normalize_name(x) for x in (a.aliases or [])]
        names = [n for n in names if n]
        if name_norm and name_norm in names:
            match = "exact"
        elif name_norm and len(name_norm) >= 4 and any(
            (name_norm in n) or (len(n) >= 4 and n in name_norm) for n in names
        ):
            match = "partial"
        else:
            continue
        actor_hits.append(
            schemas.LookupActorHit(
                id=a.id,
                name=a.name,
                actor_type=a.actor_type,
                aliases=a.aliases or [],
                match=match,
                cases=[_case_hit(case, "actor") for case in _cases_for_actor(a)],
            )
        )

    # --- direct case id ---------------------------------------------
    case_hits: list[schemas.LookupCaseHit] = []
    case_stmt = (
        select(models.Case)
        .options(selectinload(models.Case.interactions))
        .where(models.Case.case_id.ilike(f"%{q.strip()}%"))
    )
    for case in db.scalars(case_stmt).unique().all():
        case_hits.append(_case_hit(case, "case_id"))

    # sort: exact before partial
    contact_hits.sort(key=lambda h: 0 if h.match == "exact" else 1)
    actor_hits.sort(key=lambda h: 0 if h.match == "exact" else 1)

    total = (
        sum(len(h.cases) for h in contact_hits)
        + sum(len(h.cases) for h in actor_hits)
        + len(case_hits)
    )
    return schemas.LookupResponse(
        query=q,
        normalized=norm,
        contact_hits=contact_hits,
        actor_hits=actor_hits,
        case_hits=case_hits,
        total=total,
    )
