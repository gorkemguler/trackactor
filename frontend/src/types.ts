export interface Enums {
  actor_types: string[];
  channel_types: string[];
  case_statuses: string[];
  priorities: string[];
  directions: string[];
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Contact {
  id: number;
  actor_id: number | null;
  channel_type: string;
  value: string;
  normalized: string;
  label: string | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  last_seen: string | null;
  actor_name?: string | null;
}

export interface Actor {
  id: number;
  name: string;
  actor_type: string;
  aliases: string[];
  description: string | null;
  tlp: string;
  first_seen: string | null;
  last_seen: string | null;
  created_at: string;
  updated_at: string;
  contacts: Contact[];
  case_ids: string[];
}

export interface LinkedActor {
  id: number;
  name: string;
  actor_type: string;
  note: string | null;
}

export interface LinkedContact {
  id: number;
  channel_type: string;
  value: string;
  normalized: string;
  actor_id: number | null;
  actor_name: string | null;
  outreach_handle: string | null;
  note: string | null;
}

export interface Interaction {
  id: number;
  case_id: number;
  contact_id: number | null;
  direction: string;
  occurred_at: string;
  summary: string;
  analyst: string | null;
  created_at: string;
  contact_value: string | null;
  case_ref: string | null;
  case_title: string | null;
}

export interface CaseSummary {
  id: number;
  case_id: string;
  title: string;
  source_platform: string;
  source_url: string | null;
  status: string;
  priority: string;
  analyst: string | null;
  objective: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
  actor_count: number;
  interaction_count: number;
  last_interaction_at: string | null;
}

export interface CaseDetail extends CaseSummary {
  actors: LinkedActor[];
  contacts: LinkedContact[];
  interactions: Interaction[];
}

export interface LookupCaseHit {
  id: number;
  case_id: string;
  title: string;
  status: string;
  priority: string;
  source_platform: string;
  analyst: string | null;
  last_interaction_at: string | null;
  via: string;
}

export interface LookupContactHit {
  id: number;
  channel_type: string;
  value: string;
  normalized: string;
  label: string | null;
  is_active: boolean;
  actor_id: number | null;
  actor_name: string | null;
  match: string;
  cases: LookupCaseHit[];
}

export interface LookupActorHit {
  id: number;
  name: string;
  actor_type: string;
  aliases: string[];
  match: string;
  cases: LookupCaseHit[];
}

export interface LookupResponse {
  query: string;
  normalized: string;
  contact_hits: LookupContactHit[];
  actor_hits: LookupActorHit[];
  case_hits: LookupCaseHit[];
  total: number;
}

export interface StatusCount {
  status: string;
  count: number;
}

export interface Stats {
  total_cases: number;
  total_actors: number;
  total_contacts: number;
  total_interactions: number;
  cases_by_status: StatusCount[];
  awaiting_response: number;
  cases_without_interaction: number;
  recent_inbound: Interaction[];
}
