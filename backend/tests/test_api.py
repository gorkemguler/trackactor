def _make_actor(client, name="TestActor", contacts=None):
    body = {"name": name, "actor_type": "individual", "aliases": ["ta"], "contacts": contacts or []}
    r = client.post("/api/actors", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _make_case(client, case_id="CASE-1", **kw):
    body = {"case_id": case_id, "title": "Engagement", **kw}
    r = client.post("/api/cases", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_case_id_is_unique(client):
    _make_case(client, "DUP-1")
    r = client.post("/api/cases", json={"case_id": "DUP-1", "title": "again"})
    assert r.status_code == 409


def test_contact_normalized_on_create(client):
    actor = _make_actor(client)
    r = client.post(
        f"/api/actors/{actor['id']}/contacts",
        json={"channel_type": "telegram", "value": "https://t.me/Big_Boss"},
    )
    assert r.status_code == 201
    assert r.json()["normalized"] == "big_boss"


def test_lookup_by_contact_link_resolves_case(client):
    actor = _make_actor(
        client,
        name="LookupActor",
        contacts=[{"channel_type": "telegram", "value": "@target_handle"}],
    )
    contact_id = actor["contacts"][0]["id"]
    case = _make_case(client, "LK-1", actor_ids=[actor["id"]], contact_ids=[contact_id])

    # inbound value written differently than stored
    r = client.get("/api/lookup", params={"q": "https://t.me/target_handle"})
    data = r.json()
    assert data["normalized"] == "target_handle"
    assert data["contact_hits"], data
    hit = data["contact_hits"][0]
    assert hit["match"] == "exact"
    assert hit["actor_name"] == "LookupActor"
    assert case["case_id"] in [c["case_id"] for c in hit["cases"]]


def test_lookup_by_case_id(client):
    _make_case(client, "OPENCTI-2026-999")
    r = client.get("/api/lookup", params={"q": "2026-999"})
    assert any(c["case_id"] == "OPENCTI-2026-999" for c in r.json()["case_hits"])


def test_inbound_interaction_flips_awaiting_status(client):
    case = _make_case(client, "FLIP-1", status="awaiting_response")
    r = client.post(
        f"/api/cases/{case['id']}/interactions",
        json={"direction": "inbound", "summary": "they replied"},
    )
    assert r.status_code == 201
    assert client.get(f"/api/cases/{case['id']}").json()["status"] == "responded"


def test_link_and_unlink_actor(client):
    actor = _make_actor(client, name="LinkMe")
    case = _make_case(client, "LNK-1")
    r = client.post(f"/api/cases/{case['id']}/links", json={"actor_id": actor["id"]})
    assert r.status_code == 201
    assert len(r.json()["actors"]) == 1
    r = client.delete(f"/api/cases/{case['id']}/links/actor/{actor['id']}")
    assert r.json()["actors"] == []


def test_stats_counts(client):
    _make_actor(client, name="S1")
    _make_case(client, "S-1")
    _make_case(client, "S-2", status="awaiting_response")
    s = client.get("/api/stats").json()
    assert s["total_cases"] == 2
    assert s["total_actors"] == 1
    assert s["awaiting_response"] == 1
    assert s["cases_without_interaction"] == 2
