import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import type { LookupCaseHit, LookupResponse } from "../types";
import { Badge, ErrorNote, PriorityBadge, StatusBadge, fmtDate } from "../ui";

function CaseHitRow({ hit }: { hit: LookupCaseHit }) {
  return (
    <div className="row wrap" style={{ padding: "6px 0" }}>
      <Link to={`/cases/${hit.id}`} className="mono">
        {hit.case_id}
      </Link>
      <span className="muted">{hit.title}</span>
      <StatusBadge status={hit.status} />
      <PriorityBadge priority={hit.priority} />
      <Badge kind="gray">{hit.source_platform}</Badge>
      <span className="spacer" />
      <span className="muted">last: {fmtDate(hit.last_interaction_at)}</span>
    </div>
  );
}

export default function LookupPage() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [result, setResult] = useState<LookupResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // run once on load if the URL already carries ?q= (shareable lookup links)
  const ran = useRef(false);
  useEffect(() => {
    const initial = params.get("q");
    if (initial && !ran.current) {
      ran.current = true;
      run(initial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run(term: string) {
    const value = term.trim();
    if (!value) return;
    setLoading(true);
    setError(null);
    setParams({ q: value });
    try {
      setResult(await api.get<LookupResponse>(`/lookup?q=${encodeURIComponent(value)}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Reverse lookup</h1>
          <p>
            Paste an inbound handle, link, alias or case ID. trackactor normalises it and finds
            the matching case(s).
          </p>
        </div>
      </div>

      <form
        className="search-box"
        onSubmit={(e) => {
          e.preventDefault();
          run(q);
        }}
      >
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g.  https://t.me/some_handle   ·   @dealer   ·   broker@xmpp.is   ·   OPENCTI-2026-0042"
        />
        <button className="btn" disabled={loading}>
          {loading ? "…" : "Lookup"}
        </button>
      </form>

      <ErrorNote error={error} />

      {result && (
        <div>
          <p className="muted">
            {result.total} case match{result.total === 1 ? "" : "es"} · normalised as{" "}
            <code>{result.normalized || "—"}</code>
          </p>

          {result.total === 0 && (
            <div className="empty">
              No match. This identifier isn't linked to any tracked case yet.
            </div>
          )}

          {result.contact_hits.length > 0 && (
            <div className="hit-group">
              <div className="section-title">Contact matches</div>
              {result.contact_hits.map((h) => (
                <div className={`hit-card ${h.match}`} key={h.id}>
                  <div className="row wrap">
                    <Badge kind="blue">{h.channel_type}</Badge>
                    <span className="mono">{h.value}</span>
                    <Badge kind={h.match === "exact" ? "green" : "amber"}>{h.match}</Badge>
                    {!h.is_active && <Badge kind="gray">inactive</Badge>}
                    <span className="spacer" />
                    {h.actor_id ? (
                      <Link to={`/actors/${h.actor_id}`}>{h.actor_name}</Link>
                    ) : (
                      <span className="muted">unattributed</span>
                    )}
                  </div>
                  <div style={{ marginTop: 8 }}>
                    {h.cases.length === 0 && (
                      <span className="muted">Known contact, but no case linked.</span>
                    )}
                    {h.cases.map((c) => (
                      <CaseHitRow hit={c} key={c.id} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {result.actor_hits.length > 0 && (
            <div className="hit-group">
              <div className="section-title">Actor matches</div>
              {result.actor_hits.map((h) => (
                <div className={`hit-card ${h.match}`} key={h.id}>
                  <div className="row wrap">
                    <Link to={`/actors/${h.id}`}>{h.name}</Link>
                    <Badge kind="purple">{h.actor_type}</Badge>
                    <Badge kind={h.match === "exact" ? "green" : "amber"}>{h.match}</Badge>
                    {h.aliases.length > 0 && (
                      <span className="muted">aka {h.aliases.join(", ")}</span>
                    )}
                  </div>
                  <div style={{ marginTop: 8 }}>
                    {h.cases.length === 0 && <span className="muted">No case linked.</span>}
                    {h.cases.map((c) => (
                      <CaseHitRow hit={c} key={c.id} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {result.case_hits.length > 0 && (
            <div className="hit-group">
              <div className="section-title">Case ID matches</div>
              <div className="panel">
                {result.case_hits.map((c) => (
                  <CaseHitRow hit={c} key={c.id} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
