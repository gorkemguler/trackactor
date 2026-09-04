"""Best-effort mappers from platform exports into a trackactor case.

Each mapper returns an ImportPlan; the /api/import route applies it through the
shared upsert helpers. They are deliberately forgiving - anything they can't map
goes into `notes` rather than failing the import."""

from __future__ import annotations

from . import misp, stix, thehive
from .plan import ImportPlan

__all__ = ["ImportPlan", "build_plan"]

MAPPERS = {
    "misp": misp.plan,
    "thehive": thehive.plan,
    "stix": stix.plan,
}


def build_plan(platform: str, payload: dict) -> ImportPlan:
    if platform not in MAPPERS:
        raise ValueError(f"unknown platform {platform!r}; expected one of {sorted(MAPPERS)}")
    return MAPPERS[platform](payload)
