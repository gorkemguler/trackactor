import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, useApi } from "../api";
import { useEnums } from "../App";
import type { Actor, CaseSummary } from "../types";
import {
  ErrorNote,
  Modal,
  PriorityBadge,
  StatusBadge,
  TagInput,
  fmtDate,
} from "../ui";

const EMPTY = {
  case_id: "",
  title: "",
  source_platform: "Manual",
  source_url: "",
  status: "open",
  priority: "medium",
  analyst: "",
  objective: "",
  tags: [] as string[],
  actor_ids: [] as number[],
};

export default function CasesPage() {
  const enums = useEnums();
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const path = useMemo(() => {
    const p = new URLSearchParams();
    if (statusFilter) p.set("status", statusFilter);
    if (search.trim()) p.set("q", search.trim());
    const s = p.toString();
    return `/cases${s ? `?${s}` : ""}`;
  }, [statusFilter, search]);

  const { data, error, loading, refetch } = useApi<CaseSummary[]>(path, [path]);
  const { data: actors } = useApi<Actor[]>("/actors");

  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function create() {
    setSaving(true);
    setSaveErr(null);
    try {
      const payload = {
        ...form,
        source_url: form.source_url || null,
        analyst: form.analyst || null,
        objective: form.objective || null,
      };
      const created = await api.post<CaseSummary>("/cases", payload);
      setShowNew(false);
      setForm(EMPTY);
      refetch();
      window.location.assign(`/cases/${created.id}`);
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
          <h1>Cases</h1>
          <p>Each case binds an external ID to the actors and channels you engage.</p>
        </div>
        <button className="btn" onClick={() => setShowNew(true)}>
          + New case
        </button>
      </div>

      <div className="row wrap" style={{ marginBottom: 14 }}>
        <input
          style={{ maxWidth: 280 }}
          placeholder="Search case ID / title / analyst"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          style={{ maxWidth: 200 }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          {enums.case_statuses.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>

      <ErrorNote error={error} />

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Case ID</th>
              <th>Title</th>
              <th>Source</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Actors</th>
              <th>Last contact</th>
              <th>Analyst</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((c) => (
              <tr key={c.id}>
                <td>
                  <Link to={`/cases/${c.id}`} className="mono">
                    {c.case_id}
                  </Link>
                </td>
                <td>{c.title}</td>
                <td className="muted">{c.source_platform}</td>
                <td>
                  <StatusBadge status={c.status} />
                </td>
                <td>
                  <PriorityBadge priority={c.priority} />
                </td>
                <td className="mono">{c.actor_count}</td>
                <td className="muted">{fmtDate(c.last_interaction_at)}</td>
                <td className="muted">{c.analyst ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && data?.length === 0 && <div className="empty">No cases match.</div>}
        {loading && !data && <div className="empty">Loading…</div>}
      </div>

      {showNew && (
        <Modal title="New case" onClose={() => setShowNew(false)}>
          <ErrorNote error={saveErr} />
          <div className="grid cols-2">
            <label className="field">
              <span>Case ID *</span>
              <input
                value={form.case_id}
                onChange={(e) => setForm({ ...form, case_id: e.target.value })}
                placeholder="OPENCTI-2026-0042"
              />
            </label>
            <label className="field">
              <span>Source platform</span>
              <input
                value={form.source_platform}
                onChange={(e) => setForm({ ...form, source_platform: e.target.value })}
                placeholder="OpenCTI / MISP / TheHive / Splunk ES"
              />
            </label>
          </div>
          <label className="field">
            <span>Title *</span>
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </label>
          <label className="field">
            <span>Source URL</span>
            <input
              value={form.source_url}
              onChange={(e) => setForm({ ...form, source_url: e.target.value })}
              placeholder="deep link to the record in your platform"
            />
          </label>
          <div className="grid cols-3">
            <label className="field">
              <span>Status</span>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                {enums.case_statuses.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Priority</span>
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
              >
                {enums.priorities.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Analyst</span>
              <input
                value={form.analyst}
                onChange={(e) => setForm({ ...form, analyst: e.target.value })}
              />
            </label>
          </div>
          <label className="field">
            <span>Objective</span>
            <textarea
              value={form.objective}
              onChange={(e) => setForm({ ...form, objective: e.target.value })}
              placeholder="What are you trying to get out of this engagement?"
            />
          </label>
          <label className="field">
            <span>Tags</span>
            <TagInput
              value={form.tags}
              onChange={(tags) => setForm({ ...form, tags })}
            />
          </label>
          <label className="field">
            <span>Link actors (optional)</span>
            <select
              multiple
              value={form.actor_ids.map(String)}
              onChange={(e) =>
                setForm({
                  ...form,
                  actor_ids: Array.from(e.target.selectedOptions, (o) => Number(o.value)),
                })
              }
              style={{ minHeight: 90 }}
            >
              {actors?.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name} ({a.actor_type})
                </option>
              ))}
            </select>
          </label>
          <div className="row" style={{ marginTop: 6 }}>
            <span className="spacer" />
            <button className="btn ghost" onClick={() => setShowNew(false)}>
              Cancel
            </button>
            <button
              className="btn"
              disabled={saving || !form.case_id.trim() || !form.title.trim()}
              onClick={create}
            >
              {saving ? "Saving…" : "Create case"}
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
