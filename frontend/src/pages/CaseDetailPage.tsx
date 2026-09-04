import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, useApi } from "../api";
import { useEnums } from "../App";
import History from "../History";
import type { Actor, CaseDetail, Contact, Page, User } from "../types";
import {
  Badge,
  ErrorNote,
  Modal,
  PriorityBadge,
  StatusBadge,
  fmtDateTime,
} from "../ui";

export default function CaseDetailPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const enums = useEnums();
  const { data: c, error, refetch } = useApi<CaseDetail>(`/cases/${id}`, [id]);
  const { data: actors } = useApi<Page<Actor>>("/actors?limit=200");
  const { data: contacts } = useApi<Page<Contact>>("/contacts?limit=200");
  const { data: users } = useApi<User[]>("/users");

  const [busyErr, setBusyErr] = useState<string | null>(null);
  const [showLink, setShowLink] = useState(false);
  const [showLog, setShowLog] = useState(false);

  if (error) return <ErrorNote error={error} />;
  if (!c) return <div className="empty">Loading…</div>;

  async function patch(body: Record<string, unknown>) {
    setBusyErr(null);
    try {
      await api.patch(`/cases/${id}`, body);
      refetch();
    } catch (e) {
      setBusyErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function removeActor(actorId: number) {
    await api.del(`/cases/${id}/links/actor/${actorId}`);
    refetch();
  }
  async function removeContact(contactId: number) {
    await api.del(`/cases/${id}/links/contact/${contactId}`);
    refetch();
  }
  async function deleteCase() {
    if (!confirm(`Delete case ${c!.case_id}? This cannot be undone.`)) return;
    await api.del(`/cases/${id}`);
    nav("/cases");
  }

  return (
    <>
      <div className="page-head">
        <div>
          <Link to="/cases" className="muted">
            ← Cases
          </Link>
          <h1 className="mono">{c.case_id}</h1>
          <p>{c.title}</p>
        </div>
        <div className="row">
          <select value={c.status} onChange={(e) => patch({ status: e.target.value })}>
            {enums.case_statuses.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <a
            className="btn ghost sm"
            href={`/api/cases/${c.id}/export`}
            download={`${c.case_id}.trackactor.json`}
          >
            Export
          </a>
          <button className="btn danger sm" onClick={deleteCase}>
            Delete
          </button>
        </div>
      </div>

      <ErrorNote error={busyErr} />

      <div className="grid cols-2">
        <div className="panel">
          <dl className="kv">
            <dt>Status</dt>
            <dd>
              <StatusBadge status={c.status} />
            </dd>
            <dt>Priority</dt>
            <dd>
              <PriorityBadge priority={c.priority} />
            </dd>
            <dt>Source</dt>
            <dd>
              {c.source_url ? (
                <a href={c.source_url} target="_blank" rel="noreferrer">
                  {c.source_platform} ↗
                </a>
              ) : (
                c.source_platform
              )}
            </dd>
            <dt>Analyst</dt>
            <dd>{c.analyst ?? "—"}</dd>
            <dt>Assignee</dt>
            <dd>
              <select
                value={c.assignee ?? ""}
                onChange={(e) => {
                  const u = users?.find((x) => x.username === e.target.value);
                  patch({ assignee_id: u ? u.id : null });
                }}
                style={{ maxWidth: 180 }}
              >
                <option value="">unassigned</option>
                {c.assignee && !users?.some((u) => u.username === c.assignee) && (
                  <option value={c.assignee}>{c.assignee}</option>
                )}
                {users?.map((u) => (
                  <option key={u.id} value={u.username}>
                    {u.username}
                  </option>
                ))}
              </select>
            </dd>
            <dt>Created</dt>
            <dd className="muted">
              {fmtDateTime(c.created_at)}
              {c.created_by && ` · by ${c.created_by}`}
            </dd>
            <dt>Tags</dt>
            <dd className="row wrap">
              {c.tags.length ? (
                c.tags.map((t) => <Badge key={t}>{t}</Badge>)
              ) : (
                <span className="muted">—</span>
              )}
            </dd>
          </dl>
          {c.objective && (
            <>
              <div className="section-title">Objective</div>
              <p>{c.objective}</p>
            </>
          )}
        </div>

        <div className="panel">
          <div className="row">
            <div className="section-title" style={{ marginTop: 0, flex: 1 }}>
              Linked actors &amp; contacts
            </div>
            <button className="btn ghost sm" onClick={() => setShowLink(true)}>
              + Link
            </button>
          </div>

          {c.actors.length === 0 && c.contacts.length === 0 && (
            <div className="muted">Nothing linked yet.</div>
          )}

          {c.actors.map((a) => (
            <div className="row wrap" key={`a-${a.id}`} style={{ padding: "5px 0" }}>
              <Badge kind="purple">actor</Badge>
              <Link to={`/actors/${a.id}`}>{a.name}</Link>
              <span className="muted">{a.actor_type}</span>
              <span className="spacer" />
              <button className="btn ghost sm" onClick={() => removeActor(a.id)}>
                unlink
              </button>
            </div>
          ))}
          {c.contacts.map((ct) => (
            <div className="row wrap" key={`c-${ct.id}`} style={{ padding: "5px 0" }}>
              <Badge kind="blue">{ct.channel_type}</Badge>
              <span className="mono">{ct.value}</span>
              {ct.actor_name && (
                <Link to={`/actors/${ct.actor_id}`} className="muted">
                  {ct.actor_name}
                </Link>
              )}
              {ct.outreach_handle && (
                <span className="muted">via {ct.outreach_handle}</span>
              )}
              <span className="spacer" />
              <button className="btn ghost sm" onClick={() => removeContact(ct.id)}>
                unlink
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="row" style={{ marginTop: 24 }}>
        <div className="section-title" style={{ marginTop: 0, flex: 1 }}>
          Interaction log ({c.interactions.length})
        </div>
        <button className="btn sm" onClick={() => setShowLog(true)}>
          + Log message
        </button>
      </div>
      <div className="panel">
        {c.interactions.length === 0 && (
          <div className="muted">No messages logged yet.</div>
        )}
        <div className="timeline">
          {c.interactions
            .slice()
            .reverse()
            .map((i) => (
              <div className="timeline-item" key={i.id}>
                <div>
                  <span className={i.direction === "inbound" ? "dir-in" : "dir-out"}>
                    {i.direction === "inbound" ? "◀ IN" : "OUT ▶"}
                  </span>
                  <div className="muted" style={{ fontSize: 12 }}>
                    {fmtDateTime(i.occurred_at)}
                  </div>
                </div>
                <div>
                  <div>{i.summary}</div>
                  <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
                    {i.contact_value && <span className="mono">{i.contact_value} · </span>}
                    {i.analyst ?? "unknown analyst"}
                    <button
                      className="btn ghost sm"
                      style={{ marginLeft: 8 }}
                      onClick={async () => {
                        await api.del(`/cases/${id}/interactions/${i.id}`);
                        refetch();
                      }}
                    >
                      delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>

      <div style={{ marginTop: 24 }}>
        <History entityType="case" entityId={id!} />
      </div>

      {showLink && (
        <LinkModal
          caseId={Number(id)}
          actors={actors?.items ?? []}
          contacts={contacts?.items ?? []}
          channelTypes={enums.channel_types}
          onClose={() => setShowLink(false)}
          onDone={() => {
            setShowLink(false);
            refetch();
          }}
        />
      )}
      {showLog && (
        <LogModal
          caseId={Number(id)}
          contacts={c.contacts}
          directions={enums.directions}
          defaultAnalyst={c.analyst}
          onClose={() => setShowLog(false)}
          onDone={() => {
            setShowLog(false);
            refetch();
          }}
        />
      )}
    </>
  );
}

function LinkModal({
  caseId,
  actors,
  contacts,
  channelTypes,
  onClose,
  onDone,
}: {
  caseId: number;
  actors: Actor[];
  contacts: Contact[];
  channelTypes: string[];
  onClose: () => void;
  onDone: () => void;
}) {
  const [mode, setMode] = useState<"existing" | "new">("existing");
  const [actorId, setActorId] = useState<number | "">("");
  const [contactId, setContactId] = useState<number | "">("");
  const [outreach, setOutreach] = useState("");
  const [note, setNote] = useState("");
  // new-channel fields
  const [channelType, setChannelType] = useState(channelTypes[0] ?? "other");
  const [value, setValue] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit() {
    setSaving(true);
    setErr(null);
    try {
      if (mode === "new") {
        if (!value.trim()) {
          setErr("Enter the handle or link.");
          return;
        }
        await api.post(`/cases/${caseId}/contacts`, {
          channel_type: channelType,
          value: value.trim(),
          actor_id: actorId === "" ? null : actorId,
          outreach_handle: outreach || null,
        });
      } else {
        if (actorId === "" && contactId === "") {
          setErr("Pick an actor or a contact.");
          return;
        }
        await api.post(`/cases/${caseId}/links`, {
          actor_id: actorId === "" ? null : actorId,
          contact_id: contactId === "" ? null : contactId,
          outreach_handle: outreach || null,
          note: note || null,
        });
      }
      onDone();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Link actor / channel" onClose={onClose}>
      <div className="tabs" style={{ marginBottom: 14 }}>
        <button
          className={mode === "existing" ? "active" : ""}
          onClick={() => setMode("existing")}
        >
          Existing
        </button>
        <button className={mode === "new" ? "active" : ""} onClick={() => setMode("new")}>
          New channel
        </button>
      </div>
      <ErrorNote error={err} />

      {mode === "new" && (
        <div className="row" style={{ gap: 10 }}>
          <label className="field" style={{ flex: "0 0 130px" }}>
            <span>Channel</span>
            <select value={channelType} onChange={(e) => setChannelType(e.target.value)}>
              {channelTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="field" style={{ flex: 1 }}>
            <span>Handle / link</span>
            <input
              className="mono"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="@handle · https://t.me/handle"
            />
          </label>
        </div>
      )}

      <label className="field">
        <span>Actor {mode === "new" && <span className="hint">— attribute the channel</span>}</span>
        <select
          value={actorId}
          onChange={(e) => setActorId(e.target.value ? Number(e.target.value) : "")}
        >
          <option value="">—</option>
          {actors.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} ({a.actor_type})
            </option>
          ))}
        </select>
      </label>

      {mode === "existing" && (
        <label className="field">
          <span>Contact / channel</span>
          <select
            value={contactId}
            onChange={(e) => setContactId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">—</option>
            {contacts.map((ct) => (
              <option key={ct.id} value={ct.id}>
                [{ct.channel_type}] {ct.value}
                {ct.actor_name ? ` — ${ct.actor_name}` : ""}
              </option>
            ))}
          </select>
        </label>
      )}

      <label className="field">
        <span>Our outreach handle (optional)</span>
        <input value={outreach} onChange={(e) => setOutreach(e.target.value)} />
      </label>
      {mode === "existing" && (
        <label className="field">
          <span>Note (optional)</span>
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
      )}

      <div className="row">
        <span className="spacer" />
        <button className="btn ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn" disabled={saving} onClick={submit}>
          {saving ? "…" : mode === "new" ? "Add & link" : "Link"}
        </button>
      </div>
    </Modal>
  );
}

function LogModal({
  caseId,
  contacts,
  directions,
  defaultAnalyst,
  onClose,
  onDone,
}: {
  caseId: number;
  contacts: CaseDetail["contacts"];
  directions: string[];
  defaultAnalyst: string | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const [direction, setDirection] = useState("outbound");
  const [summary, setSummary] = useState("");
  const [contactId, setContactId] = useState<number | "">(
    contacts.length === 1 ? contacts[0].id : "",
  );
  const [analyst, setAnalyst] = useState(defaultAnalyst ?? "");
  const [occurredAt, setOccurredAt] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!summary.trim()) {
      setErr("Summary is required.");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      await api.post(`/cases/${caseId}/interactions`, {
        direction,
        summary: summary.trim(),
        analyst: analyst || null,
        contact_id: contactId === "" ? null : contactId,
        occurred_at: occurredAt ? new Date(occurredAt).toISOString() : null,
      });
      onDone();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Log a message" onClose={onClose}>
      <ErrorNote error={err} />
      <div className="grid cols-2">
        <label className="field">
          <span>Direction</span>
          <select value={direction} onChange={(e) => setDirection(e.target.value)}>
            {directions.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>When (optional)</span>
          <input
            type="datetime-local"
            value={occurredAt}
            onChange={(e) => setOccurredAt(e.target.value)}
          />
        </label>
      </div>
      <label className="field">
        <span>Channel used</span>
        <select
          value={contactId}
          onChange={(e) => setContactId(e.target.value ? Number(e.target.value) : "")}
        >
          <option value="">—</option>
          {contacts.map((ct) => (
            <option key={ct.id} value={ct.id}>
              [{ct.channel_type}] {ct.value}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Summary *</span>
        <textarea value={summary} onChange={(e) => setSummary(e.target.value)} />
      </label>
      <label className="field">
        <span>Analyst</span>
        <input value={analyst} onChange={(e) => setAnalyst(e.target.value)} />
      </label>
      <div className="row">
        <span className="spacer" />
        <button className="btn ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn" disabled={saving} onClick={submit}>
          {saving ? "…" : "Log"}
        </button>
      </div>
    </Modal>
  );
}
