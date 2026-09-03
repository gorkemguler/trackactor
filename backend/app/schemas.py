"""Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# --- shared -----------------------------------------------------------------

ACTOR_TYPES = [
    "unknown",
    "individual",
    "group",
    "ransomware",
    "initial_access_broker",
    "vendor",
    "hacktivist",
    "state_sponsored",
]
CHANNEL_TYPES = [
    "telegram",
    "xmpp",
    "tox",
    "session",
    "email",
    "forum",
    "discord",
    "matrix",
    "signal",
    "qq",
    "wickr",
    "url",
    "phone",
    "other",
]
CASE_STATUSES = ["open", "tracking", "awaiting_response", "responded", "closed"]
PRIORITIES = ["low", "medium", "high", "critical"]
DIRECTIONS = ["inbound", "outbound"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


# --- Contact --------------------------------------------------------------


class ContactBase(BaseModel):
    channel_type: str = "other"
    value: str = Field(min_length=1, max_length=500)
    label: str | None = None
    is_active: bool = True
    notes: str | None = None


class ContactCreate(ContactBase):
    actor_id: int | None = None


class ContactUpdate(BaseModel):
    channel_type: str | None = None
    value: str | None = Field(default=None, min_length=1, max_length=500)
    label: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    actor_id: int | None = None


class ContactOut(ORMModel, ContactBase):
    id: int
    actor_id: int | None
    normalized: str
    created_at: datetime
    last_seen: datetime | None = None


class ContactWithActor(ContactOut):
    actor_name: str | None = None


# --- Actor ---------------------------------------------------------------


class ActorBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    actor_type: str = "unknown"
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    tlp: str = "AMBER"
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class ActorCreate(ActorBase):
    contacts: list[ContactBase] = Field(default_factory=list)


class ActorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    actor_type: str | None = None
    aliases: list[str] | None = None
    description: str | None = None
    tlp: str | None = None
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class ActorOut(ORMModel, ActorBase):
    id: int
    created_at: datetime
    updated_at: datetime


class ActorDetail(ActorOut):
    contacts: list[ContactOut] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)


# --- Case --------------------------------------------------------------


class CaseBase(BaseModel):
    case_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=255)
    source_platform: str = "Manual"
    source_url: str | None = None
    status: str = "open"
    priority: str = "medium"
    analyst: str | None = None
    objective: str | None = None
    tags: list[str] = Field(default_factory=list)


class CaseCreate(CaseBase):
    actor_ids: list[int] = Field(default_factory=list)
    contact_ids: list[int] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    case_id: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    source_platform: str | None = None
    source_url: str | None = None
    status: str | None = None
    priority: str | None = None
    analyst: str | None = None
    objective: str | None = None
    tags: list[str] | None = None


class LinkedActor(BaseModel):
    id: int
    name: str
    actor_type: str
    note: str | None = None


class LinkedContact(BaseModel):
    id: int
    channel_type: str
    value: str
    normalized: str
    actor_id: int | None = None
    actor_name: str | None = None
    outreach_handle: str | None = None
    note: str | None = None


class CaseOut(ORMModel, CaseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    actor_count: int = 0
    interaction_count: int = 0
    last_interaction_at: datetime | None = None


class CaseDetail(CaseOut):
    actors: list[LinkedActor] = Field(default_factory=list)
    contacts: list[LinkedContact] = Field(default_factory=list)
    interactions: list["InteractionOut"] = Field(default_factory=list)


class CaseLinkRequest(BaseModel):
    actor_id: int | None = None
    contact_id: int | None = None
    outreach_handle: str | None = None
    note: str | None = None


# --- Interaction -------------------------------------------------------


class InteractionBase(BaseModel):
    direction: str = "outbound"
    occurred_at: datetime | None = None
    summary: str = Field(min_length=1)
    analyst: str | None = None
    contact_id: int | None = None


class InteractionCreate(InteractionBase):
    pass


class InteractionUpdate(BaseModel):
    direction: str | None = None
    occurred_at: datetime | None = None
    summary: str | None = Field(default=None, min_length=1)
    analyst: str | None = None
    contact_id: int | None = None


class InteractionOut(ORMModel, InteractionBase):
    id: int
    case_id: int
    occurred_at: datetime
    created_at: datetime
    contact_value: str | None = None
    case_ref: str | None = None
    case_title: str | None = None


# --- Lookup ----------------------------------------------------------


class LookupCaseHit(BaseModel):
    id: int
    case_id: str
    title: str
    status: str
    priority: str
    source_platform: str
    analyst: str | None = None
    last_interaction_at: datetime | None = None
    via: str  # how we got here: "contact" | "actor" | "case_id"


class LookupContactHit(BaseModel):
    id: int
    channel_type: str
    value: str
    normalized: str
    label: str | None = None
    is_active: bool
    actor_id: int | None = None
    actor_name: str | None = None
    match: str  # "exact" | "partial"
    cases: list[LookupCaseHit] = Field(default_factory=list)


class LookupActorHit(BaseModel):
    id: int
    name: str
    actor_type: str
    aliases: list[str] = Field(default_factory=list)
    match: str
    cases: list[LookupCaseHit] = Field(default_factory=list)


class LookupResponse(BaseModel):
    query: str
    normalized: str
    contact_hits: list[LookupContactHit] = Field(default_factory=list)
    actor_hits: list[LookupActorHit] = Field(default_factory=list)
    case_hits: list[LookupCaseHit] = Field(default_factory=list)
    total: int = 0


# --- Stats ---------------------------------------------------------


class StatusCount(BaseModel):
    status: str
    count: int


class Stats(BaseModel):
    total_cases: int
    total_actors: int
    total_contacts: int
    total_interactions: int
    cases_by_status: list[StatusCount]
    awaiting_response: int
    cases_without_interaction: int
    recent_inbound: list[InteractionOut] = Field(default_factory=list)


# --- Capture (one-shot: case + actor + contact + message) ---------


class CaptureCase(BaseModel):
    case_id: str = Field(min_length=1, max_length=120)
    title: str | None = None  # only used when the case is created
    source_platform: str | None = None
    source_url: str | None = None
    status: str | None = None
    priority: str | None = None
    analyst: str | None = None


class CaptureActor(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    actor_type: str = "unknown"
    aliases: list[str] = Field(default_factory=list)


class CaptureContact(BaseModel):
    channel_type: str = "other"
    value: str = Field(min_length=1, max_length=500)
    label: str | None = None


class CaptureInteraction(BaseModel):
    direction: str = "outbound"
    summary: str = Field(min_length=1)
    occurred_at: datetime | None = None
    analyst: str | None = None


class CapturePayload(BaseModel):
    case: CaptureCase
    actor: CaptureActor | None = None
    contact: CaptureContact | None = None
    interaction: CaptureInteraction | None = None


class CaptureResult(BaseModel):
    case: "CaseDetail"
    created: dict[str, bool]


# --- API keys ----------------------------------------------------


class ApiKeyCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    scope: str = "read"  # read | write


class ApiKeyOut(ORMModel):
    id: int
    label: str
    prefix: str
    scope: str
    revoked: bool
    last_used_at: datetime | None = None
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    key: str  # full key, shown only on creation


# --- Webhooks ---------------------------------------------------


class WebhookCreate(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    secret: str = Field(min_length=1, max_length=120)
    events: list[str] = Field(default_factory=lambda: ["*"])
    active: bool = True


class WebhookUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=1, max_length=500)
    secret: str | None = Field(default=None, min_length=1, max_length=120)
    events: list[str] | None = None
    active: bool | None = None


class WebhookOut(ORMModel):
    id: int
    url: str
    events: list[str]
    active: bool
    last_status: int | None = None
    last_attempt_at: datetime | None = None
    failure_count: int
    created_at: datetime


CaseDetail.model_rebuild()
CaptureResult.model_rebuild()
