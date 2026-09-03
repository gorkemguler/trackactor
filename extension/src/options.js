import { getConfig, setConfig, api } from "./lib/api.js";

const $ = (id) => document.getElementById(id);

function note(text, kind = "err") {
  $("out").innerHTML = text ? `<div class="msg ${kind}">${text}</div>` : "";
}

(async function load() {
  const cfg = await getConfig();
  $("baseUrl").value = cfg.baseUrl;
  $("apiKey").value = cfg.apiKey;
})();

// A non-localhost URL needs an explicit host permission grant.
async function ensurePermission(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return true;
  }
  if (parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1") return true;
  const origins = [parsed.origin + "/*"];
  if (await chrome.permissions.contains({ origins })) return true;
  return chrome.permissions.request({ origins });
}

function readUrl() {
  return $("baseUrl").value.trim().replace(/\/+$/, "");
}

$("save").addEventListener("click", async () => {
  const baseUrl = readUrl();
  if (!/^https?:\/\//.test(baseUrl)) {
    note("URL must start with http:// or https://");
    return;
  }
  const granted = await ensurePermission(baseUrl);
  await setConfig({ baseUrl, apiKey: $("apiKey").value.trim() });
  if (granted) note("Saved.", "ok");
  else note("Saved, but host permission was declined - requests to it will fail.", "warn");
});

$("test").addEventListener("click", async () => {
  await setConfig({ baseUrl: readUrl(), apiKey: $("apiKey").value.trim() });
  note("Testing…", "warn");
  try {
    const h = await api.health();
    note(`Connected to trackactor v${h.version}.`, "ok");
  } catch (e) {
    note(e.message);
  }
});
