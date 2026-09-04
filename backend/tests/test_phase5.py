"""v0.6 - importers, attachments, dedup."""

# --- 5.1 importers ---------------------------------------------------

STIX_BUNDLE = {
    "type": "bundle",
    "objects": [
        {
            "type": "incident",
            "id": "incident--1",
            "name": "Access broker follow-up",
            "external_references": [
                {"source_name": "OpenCTI", "external_id": "OPENCTI-2026-9001",
                 "url": "https://opencti.local/incident/1"}
            ],
        },
        {"type": "threat-actor", "id": "ta--1", "name": "n3tw0rm", "aliases": ["netw0rm"]},
        {"type": "user-account", "id": "ua--1", "account_type": "telegram", "account_login": "n3tw0rm_biz"},
        {"type": "email-addr", "id": "em--1", "value": "n3tw0rm@xmpp.jp"},
    ],
}

MISP_EVENT = {
    "Event": {
        "id": "42",
        "uuid": "misp-uuid-42",
        "info": "Ransomware affiliate infra",
        "Tag": [{"name": "tlp:amber"}, {"name": "ransomware"}],
        "Galaxy": [
            {
                "type": "mitre-threat-actor",
                "GalaxyCluster": [{"value": "LockBit", "meta": {"synonyms": ["LockBitSupp"]}}],
            }
        ],
        "Attribute": [
            {"type": "email-src", "value": "support@lockbit.example"},
            {"type": "link", "value": "http://lockbitapt.uz/contact"},
            {"type": "ip-src", "value": "1.2.3.4"},
        ],
    }
}

THEHIVE_CASE = {
    "number": 1337,
    "title": "IAB monitoring - sanitised listing",
    "description": "Broker on XSS selling VPN access.",
    "severity": 3,
    "observables": [
        {"dataType": "mail", "data": "dealer@jabber.ru"},
        {"dataType": "url", "data": "https://xss.is/members/88213/"},
    ],
}


def test_import_stix(client):
    r = client.post("/api/import", json={"platform": "stix", "payload": STIX_BUNDLE})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["case"]["case_id"] == "OPENCTI-2026-9001"
    assert body["actors_created"] == 1
    assert {c["value"] for c in body["case"]["contacts"]} == {"n3tw0rm_biz", "n3tw0rm@xmpp.jp"}
    assert body["case"]["actors"][0]["name"] == "n3tw0rm"


def test_import_misp(client):
    r = client.post("/api/import", json={"platform": "misp", "payload": MISP_EVENT})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["case"]["case_id"] == "misp-uuid-42"
    assert body["case"]["actors"][0]["name"] == "LockBit"
    values = {c["value"] for c in body["case"]["contacts"]}
    assert "support@lockbit.example" in values and "http://lockbitapt.uz/contact" in values


def test_import_thehive(client):
    r = client.post("/api/import", json={"platform": "thehive", "payload": THEHIVE_CASE})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["case"]["case_id"] == "THEHIVE-1337"
    assert body["case"]["priority"] == "high"
    assert any("actors are not mapped" in n for n in body["notes"])


def test_import_bad_payload(client):
    r = client.post("/api/import", json={"platform": "misp", "payload": {"nope": 1}})
    assert r.status_code == 422
    r = client.post("/api/import", json={"platform": "bogus", "payload": {}})
    assert r.status_code == 422


def test_import_is_idempotent(client):
    p = {"platform": "stix", "payload": STIX_BUNDLE}
    client.post("/api/import", json=p)
    second = client.post("/api/import", json=p).json()
    assert second["case_created"] is False
    assert second["actors_created"] == 0
    assert len(second["case"]["contacts"]) == 2


# --- 5.2 attachments ----------------------------------------------


def _case(client, cid="ATT-1"):
    return client.post("/api/cases", json={"case_id": cid, "title": cid}).json()


def test_attachment_roundtrip(client):
    case = _case(client)
    r = client.post(
        f"/api/cases/{case['id']}/attachments",
        files={"file": ("proof.txt", b"sample chat log", "text/plain")},
        data={"tlp": "RED"},
    )
    assert r.status_code == 201, r.text
    att = r.json()
    assert att["filename"] == "proof.txt" and att["tlp"] == "RED" and att["size"] == 15

    listed = client.get(f"/api/cases/{case['id']}/attachments").json()
    assert len(listed) == 1

    dl = client.get(f"/api/attachments/{att['id']}")
    assert dl.content == b"sample chat log"
    assert "proof.txt" in dl.headers["content-disposition"]

    assert client.delete(f"/api/attachments/{att['id']}").status_code == 204
    assert client.get(f"/api/cases/{case['id']}/attachments").json() == []


def test_attachment_size_limit(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_upload_mb", 0)  # 0 MB -> anything non-empty is too big
    case = _case(client, "ATT-2")
    r = client.post(
        f"/api/cases/{case['id']}/attachments",
        files={"file": ("big.bin", b"x" * 10, "application/octet-stream")},
    )
    assert r.status_code == 413


def test_attachment_records_audit(client):
    case = _case(client, "ATT-3")
    client.post(
        f"/api/cases/{case['id']}/attachments",
        files={"file": ("a.txt", b"hi", "text/plain")},
    )
    ev = client.get("/api/audit", params={"entity_type": "case", "entity_id": case["id"]}).json()
    assert any("attached a.txt" in e["summary"] for e in ev["items"])


def test_attachment_serializes_with_an_uploader(client):
    from app.database import SessionLocal
    from app.models import User
    from app.security import hash_password

    db = SessionLocal()
    db.add(User(username="up1", password_hash=hash_password("pw123456")))
    db.commit()
    db.close()
    client.post("/api/auth/login", json={"username": "up1", "password": "pw123456"})

    case = _case(client, "ATT-4")
    r = client.post(
        f"/api/cases/{case['id']}/attachments",
        files={"file": ("e.txt", b"x", "text/plain")},
    )
    assert r.status_code == 201, r.text
    assert r.json()["uploaded_by"] == "up1"
    assert client.get(f"/api/cases/{case['id']}/attachments").json()[0]["uploaded_by"] == "up1"


# --- 5.4 dedup assist ------------------------------------------


def test_similar_actors(client):
    client.post("/api/actors", json={"name": "LockBitSupp", "aliases": ["putin_gay"]})
    hits = client.get("/api/actors/similar", params={"name": "lockbitsup"}).json()
    assert any(a["name"] == "LockBitSupp" for a in hits)
    assert client.get("/api/actors/similar", params={"name": "totally unrelated xyz"}).json() == []


def test_similar_contacts(client):
    actor = client.post(
        "/api/actors",
        json={"name": "dd", "contacts": [{"channel_type": "telegram", "value": "https://t.me/Dealer99"}]},
    ).json()
    assert actor  # created
    hits = client.get("/api/contacts/similar", params={"value": "@dealer99"}).json()
    assert len(hits) == 1
    assert hits[0]["normalized"] == "dealer99"
