import { useApi } from "./api";
import type { AuditEvent, Page } from "./types";
import { Badge, fmtDateTime } from "./ui";

const ACTION_KIND: Record<string, string> = {
  create: "green",
  update: "blue",
  delete: "red",
};

function changeLine(changes: AuditEvent["changes"]) {
  const keys = Object.keys(changes || {});
  if (keys.length === 0) return null;
  return (
    <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
      {keys.map((k) => {
        const [from, to] = changes[k];
        return (
          <div key={k}>
            <code>{k}</code>: {JSON.stringify(from)} → {JSON.stringify(to)}
          </div>
        );
      })}
    </div>
  );
}

export default function History({
  entityType,
  entityId,
}: {
  entityType: string;
  entityId: number | string;
}) {
  const { data } = useApi<Page<AuditEvent>>(
    `/audit?entity_type=${entityType}&entity_id=${entityId}&limit=50`,
    [entityType, entityId],
  );

  return (
    <>
      <div className="section-title">History</div>
      <div className="panel">
        {data && data.items.length === 0 && <div className="muted">No changes recorded.</div>}
        <div className="timeline">
          {data?.items.map((e) => (
            <div className="timeline-item" key={e.id}>
              <div className="muted" style={{ fontSize: 12 }}>
                {fmtDateTime(e.at)}
              </div>
              <div>
                <span className="row wrap" style={{ gap: 6 }}>
                  <Badge kind={ACTION_KIND[e.action] ?? "gray"}>{e.action}</Badge>
                  <span>{e.summary}</span>
                  <span className="muted">· {e.user_label}</span>
                </span>
                {changeLine(e.changes)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
