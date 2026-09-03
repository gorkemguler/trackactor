import { useEffect, type ReactNode } from "react";

/** Relative-ish timestamp formatting. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const now = Date.now();
  const diff = (now - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`;
  return d.toISOString().slice(0, 10);
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

const STATUS_CLASS: Record<string, string> = {
  open: "blue",
  tracking: "purple",
  awaiting_response: "amber",
  responded: "green",
  closed: "gray",
};
const PRIORITY_CLASS: Record<string, string> = {
  low: "gray",
  medium: "blue",
  high: "amber",
  critical: "red",
};
const TLP_CLASS: Record<string, string> = {
  CLEAR: "gray",
  GREEN: "green",
  AMBER: "amber",
  RED: "red",
};

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${STATUS_CLASS[status] ?? "gray"}`}>{status.replace(/_/g, " ")}</span>;
}
export function PriorityBadge({ priority }: { priority: string }) {
  return <span className={`badge ${PRIORITY_CLASS[priority] ?? "gray"}`}>{priority}</span>;
}
export function TlpBadge({ tlp }: { tlp: string }) {
  return <span className={`badge ${TLP_CLASS[tlp] ?? "gray"}`}>TLP:{tlp}</span>;
}
export function Badge({ children, kind = "gray" }: { children: ReactNode; kind?: string }) {
  return <span className={`badge ${kind}`}>{children}</span>;
}

export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="row">
          <h2 style={{ flex: 1 }}>{title}</h2>
          <button className="btn ghost sm" onClick={onClose}>
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function TagInput({
  value,
  onChange,
  placeholder,
}: {
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  return (
    <div className="pill-input">
      {value.map((tag, i) => (
        <span className="pill" key={`${tag}-${i}`}>
          {tag}
          <button
            type="button"
            onClick={() => onChange(value.filter((_, j) => j !== i))}
          >
            ✕
          </button>
        </span>
      ))}
      <input
        placeholder={placeholder ?? "add and press Enter"}
        onKeyDown={(e) => {
          const t = e.currentTarget.value.trim();
          if (e.key === "Enter" && t) {
            e.preventDefault();
            if (!value.includes(t)) onChange([...value, t]);
            e.currentTarget.value = "";
          } else if (e.key === "Backspace" && !e.currentTarget.value) {
            onChange(value.slice(0, -1));
          }
        }}
      />
    </div>
  );
}

export function ErrorNote({ error }: { error: string | null }) {
  if (!error) return null;
  return <div className="err">{error}</div>;
}

export function Pager({
  total,
  limit,
  offset,
  onOffset,
}: {
  total: number;
  limit: number;
  offset: number;
  onOffset: (next: number) => void;
}) {
  if (total <= limit) return null;
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div className="row" style={{ marginTop: 12, justifyContent: "flex-end" }}>
      <span className="muted" style={{ fontSize: 12 }}>
        {from}–{to} of {total}
      </span>
      <button
        className="btn ghost sm"
        disabled={offset === 0}
        onClick={() => onOffset(Math.max(0, offset - limit))}
      >
        ‹ Prev
      </button>
      <button
        className="btn ghost sm"
        disabled={to >= total}
        onClick={() => onOffset(offset + limit)}
      >
        Next ›
      </button>
    </div>
  );
}
