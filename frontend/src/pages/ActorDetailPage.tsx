import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, useApi } from "../api";
import { useEnums } from "../App";
import History from "../History";
import type { Actor, Interaction, Page } from "../types";
import { Badge, ErrorNote, Modal, TlpBadge, fmtDate, fmtDateTime } from "../ui";

export default function ActorDetailPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const enums = useEnums();
  const { data: a, error, refetch } = useApi<Actor>(`/actors/${id}`, [id]);
  const { data: timeline } = useApi<Page<Interaction>>(
    `/interactions?actor_id=${id}&limit=100`,
    [id],
  );
  const [showContact, setShowContact] = useState(false);
  const [busyErr, setBusyErr] = useState<string | null>(null);

  if (error) return <ErrorNote error={error} />;
  if (!a) return <div className="empty">Loading…</div>;

  async function deleteContact(cid: number) {
    setBusyErr(null);
    try {
      await api.del(`/contacts/${cid}`);
      refetch();
    } catch (e) {
      setBusyErr(e instanceof Error ? e.message : String(e));
    }
  }
  async function deleteActor() {
    if (!confirm(`Delete actor ${a!.name} and all its contacts?`)) return;
    await api.del(`/actors/${id}`);
    nav("/actors");
  }

  return (
    <>
      <div className="page-head">
        <div>
          <Link to="/actors" className="muted">
            ← Actors
          </Link>
          <h1>{a.name}</h1>
          <p className="row wrap">
            <Badge kind="purple">{a.actor_type.replace(/_/g, " ")}</Badge>
            <TlpBadge tlp={a.tlp} />
            {a.aliases.map((al) => (
              <Badge key={al}>aka {al}</Badge>
            ))}
          </p>
        </div>
        <button className="btn danger sm" onClick={deleteActor}>
          Delete
        </button>
      </div>

      <ErrorNote error={busyErr} />

      <div className="grid cols-2">
        <div className="panel">
          <dl className="kv">
            <dt>First seen</dt>
            <dd className="muted">{fmtDateTime(a.first_seen)}</dd>
            <dt>Last seen</dt>
            <dd className="muted">{fmtDateTime(a.last_seen)}</dd>
            <dt>Added</dt>
            <dd className="muted">{fmtDateTime(a.created_at)}</dd>
          </dl>
          {a.description && (
            <>
              <div className="section-title">Notes</div>
              <p>{a.description}</p>
            </>
          )}
          <div className="section-title">Linked cases</div>
          <div className="row wrap">
            {a.case_ids.length ? (
              a.case_ids.map((cid) => (
                <Badge key={cid} kind="blue">
                  {cid}
                </Badge>
              ))
            ) : (
              <span className="muted">None</span>
            )}
          </div>
        </div>

        <div className="panel">
          <div className="row">
            <div className="section-title" style={{ marginTop: 0, flex: 1 }}>
              Contacts / channels
            </div>
            <button className="btn ghost sm" onClick={() => setShowContact(true)}>
              + Add
            </button>
          </div>
          {a.contacts.length === 0 && <div className="muted">No channels recorded.</div>}
          <div className="table-wrap" style={{ border: "none" }}>
            <table>
              <tbody>
                {a.contacts.map((ct) => (
                  <tr key={ct.id}>
                    <td>
                      <Badge kind="blue">{ct.channel_type}</Badge>
                    </td>
                    <td>
                      <div className="mono">{ct.value}</div>
                      <div className="muted" style={{ fontSize: 12 }}>
                        norm: <code>{ct.normalized}</code>
                        {ct.label ? ` · ${ct.label}` : ""}
                        {ct.last_seen ? ` · last seen ${fmtDate(ct.last_seen)}` : ""}
                        {!ct.is_active ? " · inactive" : ""}
                      </div>
                    </td>
                    <td style={{ width: 40 }}>
                      <button
                        className="btn ghost sm"
                        onClick={() => deleteContact(ct.id)}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 24 }}>
        <div className="section-title" style={{ marginTop: 0 }}>
          Conversation timeline{timeline ? ` (${timeline.total})` : ""}
        </div>
        <div className="panel">
          {timeline && timeline.items.length === 0 && (
            <div className="muted">No messages logged with this actor yet.</div>
          )}
          <div className="timeline">
            {timeline?.items.map((i) => (
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
                    <Link to={`/cases/${i.case_id}`} className="mono">
                      {i.case_ref ?? `#${i.case_id}`}
                    </Link>
                    {i.contact_value && <span className="mono"> · {i.contact_value}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ marginTop: 24 }}>
        <History entityType="actor" entityId={id!} />
      </div>

      {showContact && (
        <ContactModal
          actorId={Number(id)}
          channelTypes={enums.channel_types}
          onClose={() => setShowContact(false)}
          onDone={() => {
            setShowContact(false);
            refetch();
          }}
        />
      )}
    </>
  );
}

function ContactModal({
  actorId,
  channelTypes,
  onClose,
  onDone,
}: {
  actorId: number;
  channelTypes: string[];
  onClose: () => void;
  onDone: () => void;
}) {
  const [channelType, setChannelType] = useState(channelTypes[0] ?? "other");
  const [value, setValue] = useState("");
  const [label, setLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!value.trim()) {
      setErr("Value is required.");
      return;
    }
    setSaving(true);
    setErr(null);
    try {
      await api.post(`/actors/${actorId}/contacts`, {
        channel_type: channelType,
        value: value.trim(),
        label: label || null,
        notes: notes || null,
        is_active: true,
      });
      onDone();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Add contact / channel" onClose={onClose}>
      <ErrorNote error={err} />
      <div className="grid cols-2">
        <label className="field">
          <span>Channel type</span>
          <select value={channelType} onChange={(e) => setChannelType(e.target.value)}>
            {channelTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Label (optional)</span>
          <input value={label} onChange={(e) => setLabel(e.target.value)} />
        </label>
      </div>
      <label className="field">
        <span>Value / link *</span>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="https://t.me/handle   ·   dealer@xmpp.is   ·   TOX id"
        />
      </label>
      <label className="field">
        <span>Notes</span>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      <div className="row">
        <span className="spacer" />
        <button className="btn ghost" onClick={onClose}>
          Cancel
        </button>
        <button className="btn" disabled={saving} onClick={submit}>
          {saving ? "…" : "Add"}
        </button>
      </div>
    </Modal>
  );
}
