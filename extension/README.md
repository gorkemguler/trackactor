# trackactor browser extension

Capture a case ID or a threat-actor handle into trackactor from the page you're
on, without switching tabs.

| Capture | Result | Lookup |
| --- | --- | --- |
| ![Capture form](../docs/screenshots/ext-capture.png) | ![Saved](../docs/screenshots/ext-result.png) | ![Lookup](../docs/screenshots/ext-lookup.png) |

## What it does

- **On a CTI platform** (OpenCTI, MISP, TheHive, ...) — open the popup and it
  pre-fills the case ID from your selection, the title from the page, the source
  platform from the hostname and the source URL. Review, save.
- **In a chat with an actor** (web.telegram.org) — the popup reads the open
  chat's `@handle` and title. Tick *Add a contact*, tick *Attribute to an actor*,
  enter the case ID, save. The contact is created and linked to the case in one
  request.
- **A reply came in** — the *Lookup* tab (or right-click → *Look up in
  trackactor*) resolves a handle, link or alias to the case it belongs to.

Everything goes through a single `POST /api/capture` on the backend, which
upserts the case, actor and contact and wires the links, so nothing is
duplicated if you capture the same thing twice.

## Install (unpacked)

1. Run trackactor (see the project README). Note its URL — `http://localhost:8080`
   for the Docker setup, `http://localhost:5173` in local dev.
2. Chrome / Edge → `chrome://extensions` → enable **Developer mode** →
   **Load unpacked** → select this `extension/` folder.
3. Open the extension's **Settings** and set the trackactor URL. For a
   non-localhost URL you'll be asked to grant access to that host.

Firefox: `about:debugging` → **This Firefox** → **Load Temporary Add-on** →
pick `manifest.json`. MV3 support varies by version.

## Permissions

| Permission | Why |
| --- | --- |
| `activeTab`, `scripting` | read the current selection/title when you open the popup |
| `storage` | remember the trackactor URL and API key |
| `contextMenus` | the right-click *Look up* entry |
| `host_permissions: http://localhost/*`, `http://127.0.0.1/*` | talk to a local trackactor |
| `optional_host_permissions: *://*/*` | requested only if you point it at a remote instance |

No page content is sent anywhere except the trackactor instance you configure.

## Files

```
manifest.json
src/popup.*          popup UI (Capture + Lookup)
src/options.*        instance URL + API key
src/background.js    context-menu lookup
src/content/telegram.js   reads the open chat on web.telegram.org
src/lib/api.js       config + API calls, shared
```
