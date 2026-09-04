# Integrations

trackactor exposes a plain REST API plus outbound webhooks, so it drops into
whatever automation you already run. Everything below assumes a local instance at
`http://localhost:8080`.

## Authentication

By default the API is open. To lock it down, set on the backend:

```
TRACKACTOR_REQUIRE_KEY=true
TRACKACTOR_ADMIN_TOKEN=<a long random string>
```

Then create keys from **Settings → API keys** in the UI, or:

```bash
curl -X POST localhost:8080/api/keys \
  -H "X-Admin-Token: $ADMIN_TOKEN" -H 'content-type: application/json' \
  -d '{"label":"soar-prod","scope":"write"}'
# -> {"id":1,"prefix":"tk_AbC12345","key":"tk_...full...","scope":"write",...}
```

Send the full key as `X-API-Key` on every call. `read` keys may only `GET`;
`write` keys may do anything.

## Recipe 1 — open a case from a SIEM / SOAR alert

When an alert fires, create (or reuse) the tracking case and attribute the
indicator in one call to `/api/capture`:

```bash
curl -X POST localhost:8080/api/capture \
  -H "X-API-Key: $KEY" -H 'content-type: application/json' \
  -d '{
    "case":  {"case_id":"SPLUNK-ES-90871","title":"Extortion claim - retail",
              "source_platform":"Splunk ES","source_url":"https://splunk/…"},
    "actor": {"name":"ShadowVault","actor_type":"group"},
    "contact":{"channel_type":"telegram","value":"@ShadowVaultSupport"}
  }'
```

`case_id` is your external ID — calling again with the same one links to the
existing case instead of duplicating it.

### n8n

- **HTTP Request** node, `POST` `http://trackactor:8080/api/capture`
- Header `X-API-Key` = your write key
- Body (JSON) built from the trigger, as above

### Tines

- **Send to Story → HTTP Request** action, method `POST`, same URL and header
- Body from the event with a formula, e.g. `{ "case": { "case_id": <<get_alert.id>> } }`

## Recipe 2 — get pinged when an actor replies

Add a webhook (Settings → Webhooks, or `POST /api/webhooks`) subscribed to
`interaction.inbound`:

```bash
curl -X POST localhost:8080/api/webhooks \
  -H "X-Admin-Token: $ADMIN_TOKEN" -H 'content-type: application/json' \
  -d '{"url":"https://hooks.slack.com/services/…","secret":"whsec_xxx",
       "events":["interaction.inbound"]}'
```

Each delivery is a `POST` with body:

```json
{
  "event": "interaction.inbound",
  "at": "2026-09-04T09:12:00+00:00",
  "data": {
    "case": {"id": 3, "case_id": "OPENCTI-2026-0042", "title": "…", "status": "responded", "priority": "high"},
    "interaction": {"id": 12, "direction": "inbound", "summary": "…", "occurred_at": "…", "contact": "@handle"}
  }
}
```

and header `X-Trackactor-Signature: sha256=<hmac>`. Verify it:

```python
import hmac, hashlib
expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
assert hmac.compare_digest(expected, request.headers["X-Trackactor-Signature"])
```

Events: `interaction.inbound`, `interaction.outbound`, `case.status_changed`,
`case.created`. Use `["*"]` for all. Delivery retries three times, then records
the failure on the webhook row.

## Recipe 3 — nightly export

`read` key + cron:

```bash
curl -s -H "X-API-Key: $KEY" localhost:8080/api/export/cases.csv \
  > "cases-$(date +%F).csv"
curl -s -H "X-API-Key: $KEY" localhost:8080/api/export/interactions.csv \
  > "interactions-$(date +%F).csv"
```

Per-case handoff bundle (case + actors + contacts + log + audit, one JSON file):

```bash
curl -s -H "X-API-Key: $KEY" localhost:8080/api/cases/42/export > case-42.json
```

## Recipe 4 — import from your platform

```bash
curl -X POST localhost:8080/api/import -H "X-API-Key: $KEY" \
  -H 'content-type: application/json' \
  -d "{\"platform\": \"stix\", \"payload\": $(cat bundle.json)}"
```

`platform` is `misp`, `thehive` or `stix`. Mapping is best-effort; the response
`notes` say what wasn't mapped.
