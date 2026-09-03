// Shared config + trackactor API calls. Imported by the popup, the options
// page and the service worker.

const DEFAULTS = { baseUrl: "http://localhost:8080", apiKey: "" };

export async function getConfig() {
  const stored = await chrome.storage.sync.get(DEFAULTS);
  return { ...DEFAULTS, ...stored };
}

export async function setConfig(patch) {
  await chrome.storage.sync.set(patch);
}

function normBase(url) {
  return url.replace(/\/+$/, "");
}

async function request(path, options = {}) {
  const { baseUrl, apiKey } = await getConfig();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (apiKey) headers["X-API-Key"] = apiKey;

  let res;
  try {
    res = await fetch(`${normBase(baseUrl)}${path}`, { ...options, headers });
  } catch (e) {
    throw new Error(`Can't reach trackactor at ${baseUrl} - is it running?`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* keep statusText */ }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  health: () => request("/api/health"),
  lookup: (q) => request(`/api/lookup?q=${encodeURIComponent(q)}`),
  cases: (q = "") => request(`/api/cases${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  capture: (payload) =>
    request("/api/capture", { method: "POST", body: JSON.stringify(payload) }),
};

export async function webAppUrl(path = "") {
  const { baseUrl } = await getConfig();
  return `${normBase(baseUrl)}${path}`;
}

// --- small heuristics shared by popup + content scripts ------------------

export function guessPlatform(url) {
  let host;
  try {
    host = new URL(url).hostname;
  } catch {
    return "";
  }
  const known = {
    opencti: "OpenCTI",
    misp: "MISP",
    thehive: "TheHive",
    splunk: "Splunk",
    sentinel: "Sentinel",
    intel471: "Intel 471",
    recordedfuture: "Recorded Future",
    crowdstrike: "CrowdStrike",
    mandiant: "Mandiant",
    virustotal: "VirusTotal",
  };
  for (const [k, v] of Object.entries(known)) {
    if (host.includes(k)) return v;
  }
  return host.replace(/^www\./, "");
}

export function looksLikeCaseId(s) {
  const v = (s || "").trim();
  return v.length >= 3 && v.length <= 60 && /\d/.test(v) && !/\s{2,}/.test(v) && /^[\w.:/-]+$/.test(v);
}

export function looksLikeHandle(s) {
  const v = (s || "").trim();
  if (!v || v.length > 200) return false;
  return (
    /^@?[a-z0-9_.]{3,64}$/i.test(v) ||
    /^(https?:\/\/|tg:\/\/|xmpp:|mailto:)/i.test(v) ||
    /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/i.test(v)
  );
}
