"""v0.5 - one-step contact add, actor timeline, exports."""

import csv
import io


def _case(client, cid="P4-1", **kw):
    r = client.post("/api/cases", json={"case_id": cid, "title": kw.pop("title", cid), **kw})
    assert r.status_code == 201, r.text
    return r.json()


# --- 4.1 add-and-link a channel in one step ----------------------


def test_add_case_contact_creates_and_links(client):
    actor = client.post("/api/actors", json={"name": "brokerX"}).json()
    case = _case(client, "AC-1")
    r = client.post(
        f"/api/cases/{case['id']}/contacts",
        json={"channel_type": "telegram", "value": "https://t.me/brokerX_biz", "actor_id": actor["id"]},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert len(body["contacts"]) == 1
    assert body["contacts"][0]["normalized"] == "brokerx_biz"
    assert body["contacts"][0]["actor_name"] == "brokerX"

    # a second identical add is a no-op on the link (idempotent-ish)
    r2 = client.post(
        f"/api/cases/{case['id']}/contacts",
        json={"channel_type": "telegram", "value": "@brokerX_biz", "actor_id": actor["id"]},
    )
    assert len(r2.json()["contacts"]) == 1


# --- 4.2 actor timeline (via the existing /interactions?actor_id) ----


def test_actor_timeline(client):
    actor = client.post(
        "/api/actors",
        json={"name": "tl_actor", "contacts": [{"channel_type": "xmpp", "value": "t@jabber.ru"}]},
    ).json()
    cid = actor["contacts"][0]["id"]
    a = _case(client, "TL-A", actor_ids=[actor["id"]], contact_ids=[cid])
    b = _case(client, "TL-B", actor_ids=[actor["id"]])
    client.post(f"/api/cases/{a['id']}/interactions", json={"direction": "outbound", "summary": "on A via contact", "contact_id": cid})
    client.post(f"/api/cases/{b['id']}/interactions", json={"direction": "inbound", "summary": "on B via case link"})

    tl = client.get("/api/interactions", params={"actor_id": actor["id"]}).json()
    assert tl["total"] == 2
    assert {i["summary"] for i in tl["items"]} == {"on A via contact", "on B via case link"}


# --- 4.4 exports -------------------------------------------------


def test_cases_csv(client):
    _case(client, "CSV-1", priority="high")
    _case(client, "CSV-2")
    r = client.get("/api/export/cases.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.text)))
    ids = {row["case_id"] for row in rows}
    assert {"CSV-1", "CSV-2"} <= ids
    assert next(r for r in rows if r["case_id"] == "CSV-1")["priority"] == "high"


def test_interactions_csv(client):
    case = _case(client, "ICSV-1")
    client.post(f"/api/cases/{case['id']}/interactions", json={"direction": "inbound", "summary": "hi there"})
    r = client.get("/api/export/interactions.csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert any(row["summary"] == "hi there" and row["case_id"] == "ICSV-1" for row in rows)


def test_case_bundle_export(client):
    actor = client.post("/api/actors", json={"name": "bundle_actor"}).json()
    case = _case(client, "BND-1", actor_ids=[actor["id"]])
    client.patch(f"/api/cases/{case['id']}", json={"status": "closed"})
    bundle = client.get(f"/api/cases/{case['id']}/export").json()
    assert bundle["case"]["case_id"] == "BND-1"
    assert bundle["actors"][0]["name"] == "bundle_actor"
    assert any(e["action"] == "update" for e in bundle["audit"])
