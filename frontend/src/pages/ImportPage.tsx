import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { CaseDetail } from "../types";
import { Badge, ErrorNote } from "../ui";

const PLATFORMS = [
  { id: "stix", label: "STIX 2.1 bundle" },
  { id: "misp", label: "MISP event JSON" },
  { id: "thehive", label: "TheHive case JSON" },
];

interface ImportResult {
  case: CaseDetail;
  case_created: boolean;
  actors_created: number;
  contacts_created: number;
  notes: string[];
}

export default function ImportPage() {
  const [platform, setPlatform] = useState("stix");
  const [raw, setRaw] = useState("");
  const [result, setResult] = useState<ImportResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setErr(null);
    setResult(null);
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      setErr("That isn't valid JSON.");
      setBusy(false);
      return;
    }
    try {
      setResult(await api.post<ImportResult>("/import", { platform, payload: parsed }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Import a case</h1>
          <p>Paste an export from your platform. Mapping is best-effort — check the notes.</p>
        </div>
      </div>

      <ErrorNote error={err} />

      <label className="field" style={{ maxWidth: 260 }}>
        <span>Source</span>
        <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
          {PLATFORMS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Payload (JSON)</span>
        <textarea
          className="mono"
          style={{ minHeight: 260 }}
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder={'{ "objects": [ … ] }'}
        />
      </label>
      <button className="btn" disabled={busy || !raw.trim()} onClick={run}>
        {busy ? "Importing…" : "Import"}
      </button>

      {result && (
        <div className="panel" style={{ marginTop: 18 }}>
          <div className="row wrap" style={{ gap: 8 }}>
            <Badge kind={result.case_created ? "green" : "blue"}>
              {result.case_created ? "case created" : "case updated"}
            </Badge>
            <Link to={`/cases/${result.case.id}`} className="mono">
              {result.case.case_id}
            </Link>
            <span className="muted">
              +{result.actors_created} actors · +{result.contacts_created} contacts
            </span>
          </div>
          {result.notes.length > 0 && (
            <ul className="muted" style={{ fontSize: 13, marginTop: 10 }}>
              {result.notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </>
  );
}
