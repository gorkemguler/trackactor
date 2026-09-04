import { useRef, useState } from "react";
import { api, useApi } from "./api";
import { Badge, ErrorNote } from "./ui";

interface Attachment {
  id: number;
  filename: string;
  content_type: string;
  size: number;
  tlp: string;
  uploaded_by: string | null;
  created_at: string;
}

const TLP_KIND: Record<string, string> = {
  CLEAR: "gray",
  GREEN: "green",
  AMBER: "amber",
  RED: "red",
};

function humanSize(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export default function Evidence({ caseId }: { caseId: number | string }) {
  const { data, refetch } = useApi<Attachment[]>(`/cases/${caseId}/attachments`, [caseId]);
  const [tlp, setTlp] = useState("AMBER");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onPick(files: FileList | null) {
    if (!files || !files[0]) return;
    setBusy(true);
    setErr(null);
    try {
      const form = new FormData();
      form.append("file", files[0]);
      form.append("tlp", tlp);
      await api.upload(`/cases/${caseId}/attachments`, form);
      if (fileRef.current) fileRef.current.value = "";
      refetch();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("Delete this attachment?")) return;
    await api.del(`/attachments/${id}`);
    refetch();
  }

  return (
    <>
      <div className="section-title">Evidence</div>
      <div className="panel">
        <ErrorNote error={err} />
        <div className="row" style={{ marginBottom: 10 }}>
          <select value={tlp} onChange={(e) => setTlp(e.target.value)} style={{ maxWidth: 120 }}>
            {["CLEAR", "GREEN", "AMBER", "RED"].map((t) => (
              <option key={t} value={t}>
                TLP:{t}
              </option>
            ))}
          </select>
          <input
            ref={fileRef}
            type="file"
            disabled={busy}
            onChange={(e) => onPick(e.target.files)}
          />
        </div>

        {data && data.length === 0 && <div className="muted">Nothing attached.</div>}
        {data && data.length > 0 && (
          <table>
            <tbody>
              {data.map((a) => (
                <tr key={a.id}>
                  <td>
                    <a href={`/api/attachments/${a.id}`} download={a.filename} className="mono">
                      {a.filename}
                    </a>
                  </td>
                  <td>
                    <Badge kind={TLP_KIND[a.tlp] ?? "gray"}>TLP:{a.tlp}</Badge>
                  </td>
                  <td className="muted">{humanSize(a.size)}</td>
                  <td className="muted">{a.uploaded_by ?? "—"}</td>
                  <td style={{ width: 30 }}>
                    <button className="btn ghost sm" onClick={() => remove(a.id)}>
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
