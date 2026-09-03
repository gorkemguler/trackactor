import { Link } from "react-router-dom";
import { useApi } from "../api";
import type { Stats } from "../types";
import { ErrorNote, fmtDate } from "../ui";

export default function Dashboard() {
  const { data, error, loading } = useApi<Stats>("/stats");

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p>Engagement tracking at a glance.</p>
        </div>
        <Link className="btn" to="/lookup">
          ⌕ Reverse lookup
        </Link>
      </div>

      <ErrorNote error={error} />
      {loading && !data && <div className="empty">Loading…</div>}

      {data && (
        <>
          <div className="grid cols-4">
            <div className="stat">
              <div className="n">{data.total_cases}</div>
              <div className="l">Cases</div>
            </div>
            <div className="stat">
              <div className="n">{data.total_actors}</div>
              <div className="l">Actors</div>
            </div>
            <div className="stat">
              <div className="n">{data.total_contacts}</div>
              <div className="l">Contacts</div>
            </div>
            <div className="stat">
              <div className="n">{data.total_interactions}</div>
              <div className="l">Interactions</div>
            </div>
          </div>

          <div className="grid cols-2" style={{ marginTop: 16 }}>
            <div className="panel">
              <div className="section-title" style={{ marginTop: 0 }}>
                Cases by status
              </div>
              {data.cases_by_status.length === 0 && <div className="muted">No cases yet.</div>}
              <table>
                <tbody>
                  {data.cases_by_status.map((s) => (
                    <tr key={s.status}>
                      <td>{s.status.replace(/_/g, " ")}</td>
                      <td className="mono" style={{ textAlign: "right", width: 60 }}>
                        {s.count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="row" style={{ marginTop: 14 }}>
                <span className="badge amber">{data.awaiting_response} awaiting response</span>
                <span className="badge gray">
                  {data.cases_without_interaction} with no contact yet
                </span>
              </div>
            </div>

            <div className="panel">
              <div className="section-title" style={{ marginTop: 0 }}>
                Recent inbound replies
              </div>
              {data.recent_inbound.length === 0 && (
                <div className="muted">Nothing has replied yet.</div>
              )}
              <div className="timeline">
                {data.recent_inbound.map((i) => (
                  <div className="timeline-item" key={i.id}>
                    <div className="muted">{fmtDate(i.occurred_at)}</div>
                    <div>
                      <Link to={`/cases/${i.case_id}`}>case #{i.case_id}</Link>
                      {i.contact_value && (
                        <span className="mono muted"> · {i.contact_value}</span>
                      )}
                      <div>{i.summary}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
