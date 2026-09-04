# Changelog

## Unreleased

- Fix: attachment responses 500'd when an authenticated user uploaded (the
  serializer read the `User` relationship into a string field).
- `/api/capture` now writes to the audit trail like every other write path.
- `/api/keys`, `/api/webhooks` and user creation now also accept an admin
  **session** - and they close when the API is locked (`REQUIRE_KEY` /
  `REQUIRE_LOGIN`) but no `ADMIN_TOKEN` is set, instead of staying open.
- Dropped the unused `python-dateutil` dependency; added a `ruff.toml`.

## 0.6.0

- Import a case from a MISP event, a TheHive case or a STIX 2.1 bundle
  (`POST /api/import`) - best-effort mapping into case + actors + contacts.
- Evidence attachments per case (and per message), with a TLP marking and a
  sha256, stored on disk. `GET/POST /api/cases/{id}/attachments`,
  `GET/DELETE /api/attachments/{id}`.
- Duplicate assist: `GET /api/actors/similar`, `GET /api/contacts/similar`;
  the new-actor form warns on a near match.
- Postgres: `pool_pre_ping` and a pool size, a `--profile postgres` compose
  service, and the test suite runs against Postgres in CI.

## 0.5.0

- Add a channel and link it to a case in one step (`POST /api/cases/{id}/contacts`).
- Actor detail shows a conversation timeline merged across every case the actor is in.
- Exports: `GET /api/export/cases.csv`, `/api/export/interactions.csv`, and a
  self-contained per-case JSON bundle at `/api/cases/{id}/export`.
- Lookup bookmarklet in `extension/tools/` for browsers without the extension.
- CI (`.github/workflows/ci.yml`): lint, pytest, migrations, frontend build, docker build.
- Docker healthchecks; `web` waits for `backend` to be healthy.

## 0.4.0

- Alembic migrations; `init_db()` upgrades on startup and adopts a pre-migration DB.
- Users and server-side sessions; `TRACKACTOR_REQUIRE_LOGIN`; `python -m app.users`.
- Cases gain an assignee and a creator.
- Audit trail with before/after diffs on every case and actor change; `GET /api/audit`.

## 0.3.0

- Optional `X-API-Key` auth with read/write scopes; `TRACKACTOR_REQUIRE_KEY`.
- Outbound webhooks, HMAC-signed, retried; managed from Settings.
- `docs/integrations/` recipes.

## 0.2.0

- Paginated list endpoints (`{ items, total, limit, offset }`).
- Indexed contact lookup instead of a full scan.
- `Contact.last_seen`, updated when a message is logged.
- `GET /api/interactions` message search + a Messages page.

## 0.1.0

- Case / Actor / Contact / Interaction model, reverse lookup with identifier
  normalisation, dashboard, Docker, example seed data, browser extension.
