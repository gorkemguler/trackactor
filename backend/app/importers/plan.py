from __future__ import annotations

from dataclasses import dataclass, field

from .. import schemas


@dataclass
class ImportPlan:
    case: schemas.CaptureCase
    actors: list[schemas.CaptureActor] = field(default_factory=list)
    # (contact, actor_name or None to leave unattributed)
    contacts: list[tuple[schemas.CaptureContact, str | None]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
