"""ORM objects -> response schemas, filling in the computed and joined fields."""

from __future__ import annotations

from . import models, schemas


def interaction_out(obj: models.Interaction) -> schemas.InteractionOut:
    return schemas.InteractionOut(
        id=obj.id,
        case_id=obj.case_id,
        direction=obj.direction,
        occurred_at=obj.occurred_at,
        summary=obj.summary,
        analyst=obj.analyst,
        contact_id=obj.contact_id,
        created_at=obj.created_at,
        contact_value=obj.contact.value if obj.contact else None,
    )


def _last_interaction_at(case: models.Case):
    if not case.interactions:
        return None
    return max(i.occurred_at for i in case.interactions)


def case_out(case: models.Case) -> schemas.CaseOut:
    return schemas.CaseOut(
        id=case.id,
        case_id=case.case_id,
        title=case.title,
        source_platform=case.source_platform,
        source_url=case.source_url,
        status=case.status,
        priority=case.priority,
        analyst=case.analyst,
        objective=case.objective,
        tags=case.tags or [],
        created_at=case.created_at,
        updated_at=case.updated_at,
        actor_count=len(case.actor_links),
        interaction_count=len(case.interactions),
        last_interaction_at=_last_interaction_at(case),
    )


def case_detail(case: models.Case) -> schemas.CaseDetail:
    base = case_out(case).model_dump()
    base["actors"] = [
        schemas.LinkedActor(
            id=link.actor.id,
            name=link.actor.name,
            actor_type=link.actor.actor_type,
            note=link.note,
        )
        for link in case.actor_links
    ]
    base["contacts"] = [
        schemas.LinkedContact(
            id=link.contact.id,
            channel_type=link.contact.channel_type,
            value=link.contact.value,
            normalized=link.contact.normalized,
            actor_id=link.contact.actor_id,
            actor_name=link.contact.actor.name if link.contact.actor else None,
            outreach_handle=link.outreach_handle,
            note=link.note,
        )
        for link in case.contact_links
    ]
    base["interactions"] = [interaction_out(i) for i in case.interactions]
    return schemas.CaseDetail(**base)


def contact_out(obj: models.Contact) -> schemas.ContactOut:
    return schemas.ContactOut.model_validate(obj)


def contact_with_actor(obj: models.Contact) -> schemas.ContactWithActor:
    data = schemas.ContactOut.model_validate(obj).model_dump()
    data["actor_name"] = obj.actor.name if obj.actor else None
    return schemas.ContactWithActor(**data)


def actor_detail(obj: models.Actor) -> schemas.ActorDetail:
    data = schemas.ActorOut.model_validate(obj).model_dump()
    data["contacts"] = [contact_out(c) for c in obj.contacts]
    data["case_ids"] = sorted({link.case.case_id for link in obj.case_links})
    return schemas.ActorDetail(**data)
