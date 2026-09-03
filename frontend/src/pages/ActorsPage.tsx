import { useState } from "react";
import { Link } from "react-router-dom";
import { api, useApi } from "../api";
import { useEnums } from "../App";
import type { Actor, Page } from "../types";
import { Badge, ErrorNote, Modal, Pager, TagInput, TlpBadge } from "../ui";

const LIMIT = 50;

const EMPTY = {
  name: "",
  actor_type: "unknown",
  aliases: [] as string[],
  description: "",
  tlp: "AMBER",
};

export default function ActorsPage() {
  const enums = useEnums();
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const path = `/actors?limit=${LIMIT}&offset=${offset}${
    q.trim() ? `&q=${encodeURIComponent(q.trim())}` : ""
  }`;
  const { data, error, loading, refetch } = useApi<Page<Actor>>(path, [path]);

  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function create() {
    setSaving(true);
    setSaveErr(null);
    try {
      const created = await api.post<Actor>("/actors", {
        ...form,
        description: form.description || null,
        contacts: [],
      });
      setShowNew(false);
      setForm(EMPTY);
      refetch();
      window.location.assign(`/actors/${created.id}`);
    } catch (e) {
      setSaveErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Actors</h1>
          <p>Threat actors, their aliases and communication channels.</p>
        </div>
        <button className="btn" onClick={() => setShowNew(true)}>
          + New actor
        </button>
      </div>

      <div className="row" style={{ marginBottom: 14 }}>
        <input
          style={{ maxWidth: 280 }}
          placeholder="Search name / alias"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOffset(0);
          }}
        />
      </div>

      <ErrorNote error={error} />

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Aliases</th>
              <th>TLP</th>
              <th>Contacts</th>
              <th>Cases</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((a) => (
              <tr key={a.id}>
                <td>
                  <Link to={`/actors/${a.id}`}>{a.name}</Link>
                </td>
                <td className="muted">{a.actor_type.replace(/_/g, " ")}</td>
                <td className="muted">{a.aliases.join(", ") || "—"}</td>
                <td>
                  <TlpBadge tlp={a.tlp} />
                </td>
                <td className="mono">{a.contacts.length}</td>
                <td className="row wrap">
                  {a.case_ids.length
                    ? a.case_ids.map((cid) => (
                        <Badge key={cid} kind="blue">
                          {cid}
                        </Badge>
                      ))
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && data?.items.length === 0 && <div className="empty">No actors.</div>}
        {loading && !data && <div className="empty">Loading…</div>}
      </div>
      {data && (
        <Pager total={data.total} limit={data.limit} offset={data.offset} onOffset={setOffset} />
      )}

      {showNew && (
        <Modal title="New actor" onClose={() => setShowNew(false)}>
          <ErrorNote error={saveErr} />
          <label className="field">
            <span>Name / primary handle *</span>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <div className="grid cols-2">
            <label className="field">
              <span>Type</span>
              <select
                value={form.actor_type}
                onChange={(e) => setForm({ ...form, actor_type: e.target.value })}
              >
                {enums.actor_types.map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>TLP</span>
              <select
                value={form.tlp}
                onChange={(e) => setForm({ ...form, tlp: e.target.value })}
              >
                {["CLEAR", "GREEN", "AMBER", "RED"].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="field">
            <span>Aliases</span>
            <TagInput
              value={form.aliases}
              onChange={(aliases) => setForm({ ...form, aliases })}
            />
          </label>
          <label className="field">
            <span>Description</span>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
          <div className="row">
            <span className="spacer" />
            <button className="btn ghost" onClick={() => setShowNew(false)}>
              Cancel
            </button>
            <button
              className="btn"
              disabled={saving || !form.name.trim()}
              onClick={create}
            >
              {saving ? "Saving…" : "Create actor"}
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
