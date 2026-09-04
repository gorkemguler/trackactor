<p align="center">
  <img src="docs/banner.png" alt="trackactor" width="960">
</p>

<p align="center">
  <img src="https://github.com/gorkemguler/trackactor/actions/workflows/ci.yml/badge.svg" alt="CI">
  <img src="https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/UI-React%20%2B%20TS-3178C6?logo=react&logoColor=white" alt="React + TypeScript">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license">
  <img src="https://img.shields.io/badge/status-active%20development-brightgreen" alt="Active development">
</p>

<p align="center"><b>English</b> · <a href="README.tr.md">Türkçe</a></p>

# trackactor

Keep track of which case you're talking to a threat actor about.

## The problem

A case lands from your intel platform or SOC tooling. You reach out to the actor:
a forum PM, a Telegram account, an XMPP address, a marketplace chat. A few days
later a reply comes back from `@some_handle` and you can't remember which case it
belongs to, because by now you're running four other conversations with three
other actors.

trackactor fixes that. You bind the outreach to your existing case ID up front.
When a reply comes in, paste the handle or link into the lookup box and get the
case back, together with the actor, the linked channels and the conversation so
far.

Made for CTI teams, SOC / SOME analysts and anyone doing actor engagement who
needs a paper trail. There is a REST API so you can wire it into the tooling you
already run.

## Screenshots

**Dashboard** — open cases by status, and the replies that just came in.

![Dashboard](docs/screenshots/dashboard.png)

**Reverse lookup** — the whole point. `https://t.me/n3tw0rm_deals`,
`@n3tw0rm_deals` and `tg://resolve?domain=n3tw0rm_deals` all normalise to the
same key and resolve to the case.

![Reverse lookup](docs/screenshots/lookup.png)

**Cases** — every engagement, keyed by the ID your platform already gave it.

![Cases](docs/screenshots/cases.png)

**Case detail** — linked actors and channels, plus an inbound/outbound message log.

![Case detail](docs/screenshots/case-detail.png)

**Messages** — search the whole log across every case, filter by direction.

![Messages](docs/screenshots/messages.png)

**Settings** — API keys and signed outbound webhooks for your automation.

![Settings](docs/screenshots/settings.png)

**Audit** — every change, who made it, and the before/after.

![Audit](docs/screenshots/audit.png)

**Actor detail** — channels, the conversation timeline across every case, and history.

![Actor detail](docs/screenshots/actor-detail.png)

**Import** — pull a case in from MISP, TheHive or a STIX 2.1 bundle.

![Import](docs/screenshots/import.png)

## How it fits together

- **Case** — a tracked engagement, keyed by your external `case_id` and its
  source platform (OpenCTI, MISP, TheHive, Splunk ES, Intel 471, ...).
- **Actor** — a threat actor, group or persona, with aliases and a TLP marking.
- **Contact** — one communication identifier belonging to an actor, stored with a
  normalised form so `t.me/x`, `@x` and `tg://resolve?domain=x` all match.
- **Interaction** — an inbound or outbound message logged against a case.
- **Attachment** — an evidence file on a case (or a single message), TLP-marked
  and hashed.

A case links to one or more actors and/or directly to specific contacts, so a
reply still resolves when the identifier isn't attributed to an actor yet. Log an
inbound message on a case that is `awaiting_response` and it flips to `responded`
on its own. A case also carries an assignee and a creator, and every change to a
case or actor lands in the audit trail with a before/after diff.

## Running it

### Docker

```bash
docker compose up -d --build
```

Open http://localhost:8080. The API is proxied under `/api`, docs at
http://localhost:8080/api/docs. The SQLite database lives in the
`trackactor-data` volume.

Load the example data (optional):

```bash
docker compose exec backend python -m app.seed
```

### Local

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed          # optional example data
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on http://localhost:5173 and proxies `/api` to port 8000.

## API

Everything lives under `/api`; the full schema is at `/api/docs`. Auth is off by
default (see [Configuration](#configuration)); integration recipes are in
[docs/integrations](docs/integrations/README.md).

```bash
# create a case
curl -X POST localhost:8000/api/cases -H 'content-type: application/json' -d '{
  "case_id": "OPENCTI-2026-0042",
  "title": "LockBit affiliate outreach",
  "source_platform": "OpenCTI",
  "status": "awaiting_response"
}'

# a reply came in - which case is this?
curl 'localhost:8000/api/lookup?q=https://t.me/n3tw0rm_deals'
```

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/login` `logout`, `GET /api/auth/me` | session login for the web UI |
| `GET` | `/api/lookup?q=` | resolve a handle / link / alias / case id to case(s) |
| `POST` | `/api/capture` | upsert a case + actor + contact + message and link them, in one call |
| `GET` `POST` | `/api/cases` | list / create cases |
| `GET` `PATCH` `DELETE` | `/api/cases/{id}` | one case with its actors, contacts and log |
| `POST` | `/api/cases/{id}/links` | link an existing actor or contact to a case |
| `POST` | `/api/cases/{id}/contacts` | create a channel and link it in one step |
| `POST` | `/api/cases/{id}/interactions` | log a message |
| `GET` | `/api/cases/{id}/export` | self-contained JSON bundle for handoff |
| `GET` | `/api/export/cases.csv`, `/api/export/interactions.csv` | flat CSV dumps |
| `GET` `POST` | `/api/cases/{id}/attachments` | evidence files (multipart upload) |
| `GET` `DELETE` | `/api/attachments/{id}` | download / remove an attachment |
| `POST` | `/api/import` | import a case from `misp` / `thehive` / `stix` |
| `GET` | `/api/actors/similar?name=`, `/api/contacts/similar?value=` | near-duplicate check |
| `GET` | `/api/interactions?q=` | search the message log (`case_id`, `actor_id`, `direction` filters) |
| `GET` `POST` | `/api/actors` | actors and their aliases |
| `POST` | `/api/actors/{id}/contacts` | add a channel to an actor |
| `GET` `POST` | `/api/contacts` | search communication identifiers |
| `GET` | `/api/stats` | dashboard counters |
| `GET` | `/api/audit` | audit trail (`entity_type`, `entity_id` filters) |
| `GET` `POST` `PATCH` | `/api/users` | accounts (list open to any user; create/edit admin-guarded) |
| `GET` `POST` `DELETE` | `/api/keys` | manage API keys (admin-guarded) |
| `GET` `POST` `PATCH` `DELETE` | `/api/webhooks` | manage outbound webhooks (admin-guarded) |

List endpoints (`/api/cases`, `/api/actors`, `/api/contacts`, `/api/interactions`)
return `{ items, total, limit, offset }` and take `limit` (max 200) and `offset`.

## Browser extension

`extension/` is an unpacked MV3 extension for Chrome / Edge / Firefox. It grabs a
case ID off a CTI platform page, or the `@handle` of the Telegram Web chat you
have open, and files it against a case through `/api/capture` without leaving the
page. See [extension/README.md](extension/README.md). For lookup without
installing anything, there's a bookmarklet in
[extension/tools/](extension/tools/bookmarklet.js).

| Capture | Saved | Lookup |
| --- | --- | --- |
| ![Extension capture form](docs/screenshots/ext-capture.png) | ![Linked to the case](docs/screenshots/ext-result.png) | ![Reverse lookup in the popup](docs/screenshots/ext-lookup.png) |

## Configuration

`backend/.env`, or plain environment variables:

- `TRACKACTOR_DB_URL` — SQLAlchemy URL, default `sqlite:///./trackactor.db`
- `TRACKACTOR_CORS_ORIGINS` — comma-separated origins allowed to call the API in local dev
- `TRACKACTOR_REQUIRE_KEY` — when `true`, every `/api` call needs an `X-API-Key`; writes need a `write`-scoped key (default `false`)
- `TRACKACTOR_REQUIRE_LOGIN` — when `true`, the web UI shows a login screen and `/api` needs a session cookie (an API key still works for automation)
- `TRACKACTOR_ADMIN_TOKEN` — guards `/api/keys`, `/api/webhooks` and user creation. Open only on an otherwise-unlocked instance; once `REQUIRE_KEY` or `REQUIRE_LOGIN` is on, reach them with this token or an admin session.
- `TRACKACTOR_DATA_DIR` — where evidence files are written (default `./data`)
- `TRACKACTOR_MAX_UPLOAD_MB` — attachment size cap (default `25`)

Create the first account with `cd backend && python -m app.users add <name> --admin`
(the example seed also adds `analyst` / `analyst`). Manage keys and webhooks from
**Settings** in the UI. Webhooks POST `interaction.inbound`,
`interaction.outbound`, `case.status_changed` and `case.created`, signed with your
secret in `X-Trackactor-Signature` and retried three times.

The schema is managed with Alembic; `init_db()` runs `alembic upgrade head` on
startup and adopts a pre-migration database automatically.

SQLite is the default. For Postgres, set `TRACKACTOR_DB_URL` to a
`postgresql+psycopg://…` URL, or run the bundled service with
`docker compose --profile postgres up`. The test suite runs against both in CI.

## Stack

FastAPI, SQLAlchemy, Alembic and SQLite on the backend; React, TypeScript and
Vite on the frontend. Run the backend tests with `cd backend && pytest`.

## Notes

- Authentication is opt-in and coarse (one key = one scope; one role = admin or
  not). For anything serious, still run it on an internal network or behind your
  own proxy.
- SQLite is fine for a team. Point `TRACKACTOR_DB_URL` at Postgres if you outgrow it.

## License

MIT
