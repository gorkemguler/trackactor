<p align="center">
  <img src="docs/banner.png" alt="trackactor" width="960">
</p>

<p align="center">
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

## How it fits together

- **Case** — a tracked engagement, keyed by your external `case_id` and its
  source platform (OpenCTI, MISP, TheHive, Splunk ES, Intel 471, ...).
- **Actor** — a threat actor, group or persona, with aliases and a TLP marking.
- **Contact** — one communication identifier belonging to an actor, stored with a
  normalised form so `t.me/x`, `@x` and `tg://resolve?domain=x` all match.
- **Interaction** — an inbound or outbound message logged against a case.

A case links to one or more actors and/or directly to specific contacts, so a
reply still resolves when the identifier isn't attributed to an actor yet. Log an
inbound message on a case that is `awaiting_response` and it flips to `responded`
on its own.

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

No auth. Everything lives under `/api`; the full schema is at `/api/docs`.

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
| `GET` | `/api/lookup?q=` | resolve a handle / link / alias / case id to case(s) |
| `POST` | `/api/capture` | upsert a case + actor + contact + message and link them, in one call |
| `GET` `POST` | `/api/cases` | list / create cases |
| `GET` `PATCH` `DELETE` | `/api/cases/{id}` | one case with its actors, contacts and log |
| `POST` | `/api/cases/{id}/links` | link an actor or contact to a case |
| `POST` | `/api/cases/{id}/interactions` | log a message |
| `GET` | `/api/interactions?q=` | search the message log (`case_id`, `actor_id`, `direction` filters) |
| `GET` `POST` | `/api/actors` | actors and their aliases |
| `POST` | `/api/actors/{id}/contacts` | add a channel to an actor |
| `GET` `POST` | `/api/contacts` | search communication identifiers |
| `GET` | `/api/stats` | dashboard counters |

List endpoints (`/api/cases`, `/api/actors`, `/api/contacts`, `/api/interactions`)
return `{ items, total, limit, offset }` and take `limit` (max 200) and `offset`.

## Browser extension

`extension/` is an unpacked MV3 extension for Chrome / Edge / Firefox. It grabs a
case ID off a CTI platform page, or the `@handle` of the Telegram Web chat you
have open, and files it against a case through `/api/capture` without leaving the
page. See [extension/README.md](extension/README.md).

| Capture | Saved | Lookup |
| --- | --- | --- |
| ![Extension capture form](docs/screenshots/ext-capture.png) | ![Linked to the case](docs/screenshots/ext-result.png) | ![Reverse lookup in the popup](docs/screenshots/ext-lookup.png) |

## Configuration

`backend/.env`, or plain environment variables:

- `TRACKACTOR_DB_URL` — SQLAlchemy URL, default `sqlite:///./trackactor.db`
- `TRACKACTOR_CORS_ORIGINS` — comma-separated origins allowed to call the API in local dev

## Stack

FastAPI, SQLAlchemy and SQLite on the backend; React, TypeScript and Vite on the
frontend. Run the backend tests with `cd backend && pytest`.

## Notes

- No authentication. Run it on an internal network or behind your own auth proxy.
- SQLite is fine for a team. Point `TRACKACTOR_DB_URL` at Postgres if you outgrow it.

## License

MIT
