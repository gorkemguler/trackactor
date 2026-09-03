import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useApi } from "../api";
import { useEnums } from "../App";
import type { Interaction, Page } from "../types";
import { ErrorNote, Pager, fmtDateTime } from "../ui";

const LIMIT = 50;

export default function MessagesPage() {
  const enums = useEnums();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [direction, setDirection] = useState(params.get("direction") ?? "");
  const [offset, setOffset] = useState(0);

  const path = useMemo(() => {
    const p = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
    if (q.trim()) p.set("q", q.trim());
    if (direction) p.set("direction", direction);
    return `/interactions?${p.toString()}`;
  }, [q, direction, offset]);

  const { data, error, loading } = useApi<Page<Interaction>>(path, [path]);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setOffset(0);
    const p = new URLSearchParams();
    if (q.trim()) p.set("q", q.trim());
    if (direction) p.set("direction", direction);
    setParams(p);
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Messages</h1>
          <p>Every logged interaction across all cases.</p>
        </div>
      </div>

      <form className="row wrap" style={{ marginBottom: 16 }} onSubmit={submit}>
        <input
          style={{ maxWidth: 320 }}
          placeholder="Search summary text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          style={{ maxWidth: 160 }}
          value={direction}
          onChange={(e) => {
            setDirection(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">Any direction</option>
          {enums.directions.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <button className="btn sm">Search</button>
      </form>

      <ErrorNote error={error} />

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Dir</th>
              <th>Case</th>
              <th>Summary</th>
              <th>Channel</th>
              <th>Analyst</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((i) => (
              <tr key={i.id}>
                <td className="muted" style={{ whiteSpace: "nowrap" }}>
                  {fmtDateTime(i.occurred_at)}
                </td>
                <td>
                  <span className={i.direction === "inbound" ? "dir-in" : "dir-out"}>
                    {i.direction === "inbound" ? "IN" : "OUT"}
                  </span>
                </td>
                <td>
                  <Link to={`/cases/${i.case_id}`} className="mono">
                    {i.case_ref ?? `#${i.case_id}`}
                  </Link>
                </td>
                <td>{i.summary}</td>
                <td className="mono muted">{i.contact_value ?? "—"}</td>
                <td className="muted">{i.analyst ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && data?.items.length === 0 && (
          <div className="empty">No messages match.</div>
        )}
        {loading && !data && <div className="empty">Loading…</div>}
      </div>
      {data && (
        <Pager total={data.total} limit={data.limit} offset={data.offset} onOffset={setOffset} />
      )}
    </>
  );
}
