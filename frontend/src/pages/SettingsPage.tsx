import { useEffect, useState } from "react";
import { ADMIN_TOKEN_KEY, api, useApi } from "../api";
import type { ApiKey, ApiKeyCreated, Webhook } from "../types";
import { Badge, ErrorNote, fmtDate } from "../ui";

const WEBHOOK_EVENTS = [
  "interaction.inbound",
  "interaction.outbound",
  "case.status_changed",
  "case.created",
];

export default function SettingsPage() {
  const [adminToken, setAdminToken] = useState("");
  const [savedToken, setSavedToken] = useState("");

  useEffect(() => {
    try {
      const t = localStorage.getItem(ADMIN_TOKEN_KEY) ?? "";
      setAdminToken(t);
      setSavedToken(t);
    } catch {
      /* ignore */
    }
  }, []);

  function saveToken() {
    try {
      if (adminToken) localStorage.setItem(ADMIN_TOKEN_KEY, adminToken);
      else localStorage.removeItem(ADMIN_TOKEN_KEY);
    } catch {
      /* ignore */
    }
    setSavedToken(adminToken);
    window.location.reload();
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p>API keys and outbound webhooks for wiring trackactor into your tooling.</p>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="section-title" style={{ marginTop: 0 }}>
          Admin token
        </div>
        <p className="muted" style={{ marginTop: 0 }}>
          Only needed if the server sets <code>TRACKACTOR_ADMIN_TOKEN</code>. Stored in this
          browser and sent as <code>X-Admin-Token</code>.
        </p>
        <div className="row">
          <input
            type="password"
            placeholder="(unset)"
            value={adminToken}
            onChange={(e) => setAdminToken(e.target.value)}
            style={{ maxWidth: 320 }}
          />
          <button className="btn sm" disabled={adminToken === savedToken} onClick={saveToken}>
            Save &amp; reload
          </button>
        </div>
      </div>

      <ApiKeys />
      <Webhooks />
    </>
  );
}

function ApiKeys() {
  const { data, error, refetch } = useApi<ApiKey[]>("/keys");
  const [label, setLabel] = useState("");
  const [scope, setScope] = useState("read");
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function create() {
    setErr(null);
    try {
      setCreated(await api.post<ApiKeyCreated>("/keys", { label: label.trim(), scope }));
      setLabel("");
      refetch();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  async function revoke(id: number) {
    if (!confirm("Revoke this key? Clients using it stop working immediately.")) return;
    await api.del(`/keys/${id}`);
    refetch();
  }

  return (
    <div className="panel" style={{ marginBottom: 20 }}>
      <div className="section-title" style={{ marginTop: 0 }}>
        API keys
      </div>
      <ErrorNote error={error || err} />

      {created && (
        <div className="msg-ok">
          <div style={{ fontSize: 12, marginBottom: 4 }}>
            Copy this now — it is not shown again.
          </div>
          <code className="key-reveal">{created.key}</code>
          <button
            className="btn ghost sm"
            style={{ marginLeft: 8 }}
            onClick={() => navigator.clipboard?.writeText(created.key)}
          >
            Copy
          </button>
          <button
            className="btn ghost sm"
            style={{ marginLeft: 6 }}
            onClick={() => setCreated(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="row" style={{ margin: "10px 0" }}>
        <input
          placeholder="Label, e.g. n8n-prod"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          style={{ maxWidth: 240 }}
        />
        <select value={scope} onChange={(e) => setScope(e.target.value)} style={{ maxWidth: 140 }}>
          <option value="read">read</option>
          <option value="write">write</option>
        </select>
        <button className="btn sm" disabled={!label.trim()} onClick={create}>
          Create key
        </button>
      </div>

      {data && data.length > 0 ? (
        <div className="table-wrap" style={{ border: "none" }}>
          <table>
            <thead>
              <tr>
                <th>Label</th>
                <th>Prefix</th>
                <th>Scope</th>
                <th>Last used</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.map((k) => (
                <tr key={k.id} style={{ opacity: k.revoked ? 0.5 : 1 }}>
                  <td>{k.label}</td>
                  <td className="mono">{k.prefix}…</td>
                  <td>
                    <Badge kind={k.scope === "write" ? "amber" : "gray"}>{k.scope}</Badge>
                  </td>
                  <td className="muted">{fmtDate(k.last_used_at)}</td>
                  <td>
                    {k.revoked ? (
                      <span className="muted">revoked</span>
                    ) : (
                      <button className="btn ghost sm" onClick={() => revoke(k.id)}>
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="muted">No keys yet.</div>
      )}
    </div>
  );
}

function Webhooks() {
  const { data, error, refetch } = useApi<Webhook[]>("/webhooks");
  const [url, setUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [events, setEvents] = useState<string[]>(["*"]);
  const [err, setErr] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<Record<number, string>>({});

  function toggleEvent(ev: string) {
    setEvents((cur) => {
      if (ev === "*") return ["*"];
      const without = cur.filter((x) => x !== "*" && x !== ev);
      return cur.includes(ev) ? (without.length ? without : ["*"]) : [...without, ev];
    });
  }

  async function create() {
    setErr(null);
    try {
      await api.post("/webhooks", { url: url.trim(), secret: secret.trim(), events });
      setUrl("");
      setSecret("");
      setEvents(["*"]);
      refetch();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }
  async function test(id: number) {
    setTestResult((r) => ({ ...r, [id]: "…" }));
    try {
      const res = await api.post<{ ok: boolean; status: number | null; error?: string }>(
        `/webhooks/${id}/test`,
        {},
      );
      setTestResult((r) => ({
        ...r,
        [id]: res.ok ? `ok (${res.status})` : `failed (${res.status ?? res.error})`,
      }));
    } catch (e) {
      setTestResult((r) => ({ ...r, [id]: e instanceof Error ? e.message : "error" }));
    }
    refetch();
  }
  async function remove(id: number) {
    if (!confirm("Delete this webhook?")) return;
    await api.del(`/webhooks/${id}`);
    refetch();
  }

  return (
    <div className="panel">
      <div className="section-title" style={{ marginTop: 0 }}>
        Webhooks
      </div>
      <p className="muted" style={{ marginTop: 0 }}>
        trackactor POSTs to these on the events you pick, signed with your secret in{" "}
        <code>X-Trackactor-Signature</code>.
      </p>
      <ErrorNote error={error || err} />

      <div style={{ margin: "10px 0" }}>
        <div className="row" style={{ marginBottom: 8 }}>
          <input
            placeholder="https://your-endpoint/hook"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <input
            placeholder="signing secret"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            style={{ maxWidth: 200 }}
          />
        </div>
        <div className="row wrap" style={{ marginBottom: 8 }}>
          <label className="chk">
            <input
              type="checkbox"
              checked={events.includes("*")}
              onChange={() => toggleEvent("*")}
            />{" "}
            all events
          </label>
          {WEBHOOK_EVENTS.map((ev) => (
            <label key={ev} className="chk">
              <input
                type="checkbox"
                checked={events.includes(ev)}
                onChange={() => toggleEvent(ev)}
              />{" "}
              {ev}
            </label>
          ))}
        </div>
        <button className="btn sm" disabled={!url.trim() || !secret.trim()} onClick={create}>
          Add webhook
        </button>
      </div>

      {data && data.length > 0 ? (
        <div className="table-wrap" style={{ border: "none" }}>
          <table>
            <thead>
              <tr>
                <th>URL</th>
                <th>Events</th>
                <th>Last</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.map((h) => (
                <tr key={h.id}>
                  <td className="mono" style={{ wordBreak: "break-all" }}>
                    {h.url}
                  </td>
                  <td>
                    <span className="row wrap">
                      {h.events.map((e) => (
                        <Badge key={e}>{e}</Badge>
                      ))}
                    </span>
                  </td>
                  <td className="muted">
                    {h.last_attempt_at ? (
                      <>
                        {h.last_status ?? "err"} · {fmtDate(h.last_attempt_at)}
                        {h.failure_count > 0 && ` · ${h.failure_count} fails`}
                      </>
                    ) : (
                      "—"
                    )}
                    {testResult[h.id] && (
                      <div style={{ fontSize: 11 }}>test: {testResult[h.id]}</div>
                    )}
                  </td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn ghost sm" onClick={() => test(h.id)}>
                      Test
                    </button>{" "}
                    <button className="btn ghost sm" onClick={() => remove(h.id)}>
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="muted">No webhooks yet.</div>
      )}
    </div>
  );
}
