import {
  api,
  webAppUrl,
  guessPlatform,
  looksLikeCaseId,
  looksLikeHandle,
} from "./lib/api.js";

const $ = (id) => document.getElementById(id);

// ---- tab switching ----------------------------------------------------

function showTab(name) {
  const cap = name === "capture";
  $("tabCapture").classList.toggle("active", cap);
  $("tabLookup").classList.toggle("active", !cap);
  $("panelCapture").hidden = !cap;
  $("panelLookup").hidden = cap;
}
$("tabCapture").addEventListener("click", () => showTab("capture"));
$("tabLookup").addEventListener("click", () => showTab("lookup"));
$("openOptions").addEventListener("click", () => chrome.runtime.openOptionsPage());

// ---- collapsible sections ------------------------------------------

for (const [cb, body] of [
  ["incActor", "actorBody"],
  ["incContact", "contactBody"],
  ["incMsg", "msgBody"],
]) {
  $(cb).addEventListener("change", () => {
    $(body).hidden = !$(cb).checked;
  });
}

// ---- read the current page --------------------------------------

async function readPageContext() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const ctx = { url: tab?.url || "", title: tab?.title || "", selection: "", telegram: null };
  if (!tab?.id) return ctx;

  // try a declared content script first (telegram), then fall back to
  // an activeTab injection for the selection on any other page.
  try {
    const reply = await chrome.tabs.sendMessage(tab.id, { type: "getContext" });
    if (reply) return { ...ctx, ...reply };
  } catch { /* no content script here */ }

  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => ({
        selection: String(window.getSelection() || "").trim(),
        title: document.title,
      }),
    });
    if (result) Object.assign(ctx, result);
  } catch { /* restricted page */ }

  return ctx;
}

function cleanTitle(t) {
  if (!t) return "";
  return t.split(/\s[|–—-]\s/)[0].trim().slice(0, 120);
}

// ---- prefill the capture form ------------------------------------

async function prefill() {
  const ctx = await readPageContext();
  const sel = (ctx.selection || "").trim();
  const onTelegram = /(^|\.)web\.telegram\.org$/.test(safeHost(ctx.url));

  $("caseUrl").value = ctx.url || "";
  $("casePlatform").value = onTelegram ? "" : guessPlatform(ctx.url);
  $("caseTitle").value = cleanTitle(ctx.title);

  if (looksLikeCaseId(sel)) $("caseId").value = sel;

  const tgHandle = ctx.telegram && ctx.telegram.handle;
  const contactGuess = tgHandle || (looksLikeHandle(sel) ? sel : "");
  if (contactGuess) {
    $("incContact").checked = true;
    $("contactBody").hidden = false;
    $("contactValue").value = contactGuess;
    $("contactType").value = onTelegram || /t\.me|telegram/i.test(contactGuess) ? "telegram" : "url";

    if (ctx.telegram && ctx.telegram.title) {
      $("incActor").checked = true;
      $("actorBody").hidden = false;
      $("actorName").value = ctx.telegram.title;
    }
  }

  if (sel && !looksLikeHandle(sel) && !looksLikeCaseId(sel)) {
    $("incMsg").checked = true;
    $("msgBody").hidden = false;
    $("msgSummary").value = sel.slice(0, 500);
    $("msgDir").value = onTelegram ? "inbound" : "outbound";
  }

  // land on Lookup instead if we have a handle but no case id to work with
  if (contactGuess && !$("caseId").value) {
    $("lookupQ").value = contactGuess;
  }
}

function safeHost(u) {
  try {
    return new URL(u).hostname;
  } catch {
    return "";
  }
}

// ---- connection status ------------------------------------------

async function checkHealth() {
  try {
    const h = await api.health();
    $("dot").className = "dot ok";
    $("dot").title = `connected · v${h.version}`;
    $("foot").textContent = await webAppUrl();
  } catch (e) {
    $("dot").className = "dot bad";
    $("dot").title = e.message;
    $("foot").innerHTML = `Not connected. <a href="#" id="cfgLink">Set your trackactor URL</a>`;
    $("cfgLink")?.addEventListener("click", (ev) => {
      ev.preventDefault();
      chrome.runtime.openOptionsPage();
    });
  }
}

// ---- capture submit -------------------------------------------

function msg(el, text, kind = "err") {
  el.innerHTML = text ? `<div class="msg ${kind}">${text}</div>` : "";
}

$("saveBtn").addEventListener("click", async () => {
  const caseId = $("caseId").value.trim();
  if (!caseId) {
    msg($("captureMsg"), "A case ID is required.");
    return;
  }
  const payload = {
    case: {
      case_id: caseId,
      title: $("caseTitle").value.trim() || null,
      source_platform: $("casePlatform").value.trim() || null,
      source_url: $("caseUrl").value.trim() || null,
      priority: $("casePriority").value || null,
    },
  };
  if ($("incActor").checked && $("actorName").value.trim()) {
    payload.actor = { name: $("actorName").value.trim(), actor_type: $("actorType").value };
  }
  if ($("incContact").checked && $("contactValue").value.trim()) {
    payload.contact = {
      channel_type: $("contactType").value,
      value: $("contactValue").value.trim(),
    };
  }
  if ($("incMsg").checked && $("msgSummary").value.trim()) {
    payload.interaction = { direction: $("msgDir").value, summary: $("msgSummary").value.trim() };
  }

  $("saveBtn").disabled = true;
  $("saveBtn").textContent = "Saving…";
  msg($("captureMsg"), "");
  try {
    const res = await api.capture(payload);
    await renderResult(res);
  } catch (e) {
    msg($("captureMsg"), e.message);
  } finally {
    $("saveBtn").disabled = false;
    $("saveBtn").textContent = "Save to trackactor";
  }
});

async function renderResult(res) {
  const c = res.case;
  const made = Object.entries(res.created)
    .filter(([, v]) => v)
    .map(([k]) => k);
  const lines = [];
  lines.push(made.includes("case") ? `Created case <b>${c.case_id}</b>` : `Linked to <b>${c.case_id}</b>`);
  if (c.actors.length) lines.push(`Actor: ${c.actors.map((a) => a.name).join(", ")}`);
  if (c.contacts.length) lines.push(`Channels: ${c.contacts.length}`);
  if (made.includes("interaction")) lines.push("Message logged");

  const caseUrl = await webAppUrl(`/cases/${c.id}`);
  $("captureForm").hidden = true;
  const box = $("captureResult");
  box.hidden = false;
  box.innerHTML = `
    <div class="big">&#10003;</div>
    <div class="cid">${c.case_id}</div>
    <ul>${lines.map((l) => `<li>${l}</li>`).join("")}</ul>
    <div class="actions">
      <button class="btn" id="openCase">Open case</button>
      <button class="btn ghost" id="again">Capture another</button>
    </div>`;
  $("openCase").addEventListener("click", () => chrome.tabs.create({ url: caseUrl }));
  $("again").addEventListener("click", () => {
    box.hidden = true;
    $("captureForm").hidden = false;
  });
}

// ---- lookup --------------------------------------------------

async function runLookup() {
  const q = $("lookupQ").value.trim();
  if (!q) return;
  const out = $("lookupOut");
  out.innerHTML = `<div class="empty">Searching…</div>`;
  try {
    const r = await api.lookup(q);
    await renderLookup(r);
  } catch (e) {
    out.innerHTML = `<div class="msg err">${e.message}</div>`;
  }
}
$("lookupBtn").addEventListener("click", runLookup);
$("lookupQ").addEventListener("keydown", (e) => {
  if (e.key === "Enter") runLookup();
});

async function renderLookup(r) {
  const out = $("lookupOut");
  if (r.total === 0) {
    out.innerHTML = `<div class="empty">No case is linked to <b>${escapeHtml(r.query)}</b> yet.<br>Normalised as <code>${escapeHtml(r.normalized || "—")}</code>.</div>`;
    return;
  }
  const seen = new Set();
  const rows = [];
  const collect = (hits, match) => {
    for (const h of hits) {
      for (const c of h.cases) {
        if (seen.has(c.id)) continue;
        seen.add(c.id);
        rows.push({ ...c, match });
      }
    }
  };
  collect(r.contact_hits.filter((h) => h.match === "exact"), "exact");
  collect(r.actor_hits.filter((h) => h.match === "exact"), "exact");
  collect(r.contact_hits, "");
  collect(r.actor_hits, "");
  for (const c of r.case_hits) {
    if (!seen.has(c.id)) {
      seen.add(c.id);
      rows.push({ ...c, match: "" });
    }
  }

  const base = await webAppUrl();
  out.innerHTML = rows
    .map(
      (c) => `
      <div class="hit ${c.match}" data-url="${base}/cases/${c.id}">
        <span class="cid">${escapeHtml(c.case_id)}</span>
        <div class="ttl">${escapeHtml(c.title)}</div>
        <div class="meta">
          <span class="badge ${statusKind(c.status)}">${c.status.replace(/_/g, " ")}</span>
          <span class="badge">${escapeHtml(c.source_platform)}</span>
        </div>
      </div>`
    )
    .join("");
  out.querySelectorAll(".hit").forEach((el) =>
    el.addEventListener("click", () => chrome.tabs.create({ url: el.dataset.url }))
  );
}

function statusKind(s) {
  if (s === "responded") return "green";
  if (s === "awaiting_response") return "amber";
  return "blue";
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// ---- boot ---------------------------------------------------

checkHealth();
prefill();
