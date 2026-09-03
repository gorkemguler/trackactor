// Runs on web.telegram.org. Best-effort read of the chat you currently have
// open, so the popup can pre-fill the contact. If the DOM scrape misses, the
// analyst just selects the @handle in the message pane instead.

function readOpenChat() {
  const headers = document.querySelectorAll(
    ".chat-info, .ChatInfo, .sidebar-header, .MiddleHeader, .chat-container .top"
  );
  let title = null;
  let handle = null;

  for (const el of headers) {
    if (!el || !el.offsetParent) continue;
    const text = el.textContent || "";
    const m = text.match(/@[A-Za-z0-9_]{4,32}/);
    if (m && !handle) handle = m[0];
    const t = el.querySelector(
      ".peer-title, .user-title, .title, .fullName, .ChatInfo .title"
    );
    if (t && !title) title = (t.textContent || "").trim() || null;
  }
  return { title, handle };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "getContext") {
    sendResponse({
      selection: String(window.getSelection() || "").trim(),
      title: document.title,
      telegram: readOpenChat(),
    });
  }
  return true;
});
