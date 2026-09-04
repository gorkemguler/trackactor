import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../api";
import type { AuditEvent, Page } from "../types";
import { Badge, ErrorNote, Pager, fmtDateTime } from "../ui";

const LIMIT = 50;
const ACTION_KIND: Record<string, string> = { create: "green", update: "blue", delete: "red" };

export default function AuditPage() {
  const [entityType, setEntityType] = useState("");
  const [offset, setOffset] = useState(0);

  const path = useMemo(() => {
    const p = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
    if (entityType) p.set("entity_type", entityType);
    return `/audit?${p.toString()}`;
  }, [entityType, offset]);

  const { data, error, loading } = useApi<Page<AuditEvent>>(path, [path]);

  function link(e: AuditEvent) {
    if (e.entity_id == null) return e.entity_type;
    const to =
      e.entity_type === "case"
        ? `/cases/${e.entity_id}`
        : e.entity_type === "actor"
          ? `/actors/${e.entity_id}`
          : null;
    return to ? (
      <Link to={to} className="mono">
        {e.entity_type} #{e.entity_id}
      </Link>
    ) : (
      `${e.entity_type} #${e.entity_id}`
    );
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Audit</h1>
          <p>Every change, who made it, and what moved.</p>
        </div>
      </div>

      <div className="row" style={{ marginBottom: 14 }}>
        <select
          style={{ maxWidth: 180 }}
          value={entityType}
          onChange={(e) => {
            setEntityType(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">All entities</option>
          <option value="case">case</option>
          <option value="actor">actor</option>
        </select>
      </div>

      <ErrorNote error={error} />

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Who</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((e) => (
              <tr key={e.id}>
                <td className="muted" style={{ whiteSpace: "nowrap" }}>
                  {fmtDateTime(e.at)}
                </td>
                <td>{e.user_label}</td>
                <td>
                  <Badge kind={ACTION_KIND[e.action] ?? "gray"}>{e.action}</Badge>
                </td>
                <td>{link(e)}</td>
                <td>
                  {e.summary}
                  {Object.keys(e.changes || {}).length > 0 && (
                    <div className="muted" style={{ fontSize: 12 }}>
                      {Object.entries(e.changes).map(([k, [from, to]]) => (
                        <div key={k}>
                          <code>{k}</code>: {JSON.stringify(from)} → {JSON.stringify(to)}
                        </div>
                      ))}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && data?.items.length === 0 && (
          <div className="empty">Nothing recorded yet.</div>
        )}
        {loading && !data && <div className="empty">Loading…</div>}
      </div>
      {data && (
        <Pager total={data.total} limit={data.limit} offset={data.offset} onOffset={setOffset} />
      )}
    </>
  );
}
