"""v0.2 - pagination, indexed lookup, last_seen, message search."""


def _case(client, cid, **kw):
    r = client.post("/api/cases", json={"case_id": cid, "title": kw.pop("title", cid), **kw})
    assert r.status_code == 201, r.text
    return r.json()


# --- pagination ------------------------------------------------------


def test_cases_list_is_paginated(client):
    for i in range(7):
        _case(client, f"PAGE-{i:02d}")
    r = client.get("/api/cases", params={"limit": 3, "offset": 0}).json()
    assert r["total"] == 7
    assert r["limit"] == 3 and r["offset"] == 0
    assert len(r["items"]) == 3

    rest = client.get("/api/cases", params={"limit": 3, "offset": 6}).json()
    assert len(rest["items"]) == 1
    assert rest["total"] == 7


def test_contacts_and_actors_lists_are_paginated(client):
    for i in range(4):
        client.post(
            "/api/actors",
            json={"name": f"actor{i}", "contacts": [{"channel_type": "telegram", "value": f"@a{i}"}]},
        )
    a = client.get("/api/actors", params={"limit": 2}).json()
    assert a["total"] == 4 and len(a["items"]) == 2
    c = client.get("/api/contacts", params={"limit": 2}).json()
    assert c["total"] == 4 and len(c["items"]) == 2


def test_limit_is_capped(client):
    r = client.get("/api/cases", params={"limit": 999})
    assert r.status_code == 422  # > 200


# --- lookup stays correct with many contacts ----------------------


def test_lookup_finds_one_among_many(client):
    payload = {
        "name": "haystack",
        "contacts": [{"channel_type": "telegram", "value": f"@filler_{i}"} for i in range(200)],
    }
    payload["contacts"].append({"channel_type": "telegram", "value": "https://t.me/the_needle"})
    actor = client.post("/api/actors", json=payload).json()
    needle_id = actor["contacts"][-1]["id"]
    _case(client, "NDL-1", actor_ids=[actor["id"]], contact_ids=[needle_id])

    r = client.get("/api/lookup", params={"q": "@the_needle"}).json()
    exact = [h for h in r["contact_hits"] if h["match"] == "exact"]
    assert len(exact) == 1
    assert exact[0]["normalized"] == "the_needle"
    assert "NDL-1" in [c["case_id"] for c in exact[0]["cases"]]


# --- last_seen ----------------------------------------------------


def test_logging_an_interaction_sets_last_seen(client):
    actor = client.post(
        "/api/actors",
        json={"name": "seen_me", "contacts": [{"channel_type": "xmpp", "value": "s@jabber.ru"}]},
    ).json()
    assert actor["last_seen"] is None
    assert actor["contacts"][0]["last_seen"] is None

    case = _case(client, "SEEN-1")
    contact_id = actor["contacts"][0]["id"]
    client.post(
        f"/api/cases/{case['id']}/interactions",
        json={"direction": "outbound", "summary": "hello", "contact_id": contact_id},
    )

    fresh = client.get(f"/api/actors/{actor['id']}").json()
    assert fresh["last_seen"] is not None
    assert fresh["contacts"][0]["last_seen"] is not None


# --- message search ---------------------------------------------


def test_interaction_search(client):
    case = _case(client, "MSG-1", status="awaiting_response")
    client.post(
        f"/api/cases/{case['id']}/interactions",
        json={"direction": "outbound", "summary": "asked for 0.05 BTC proof"},
    )
    client.post(
        f"/api/cases/{case['id']}/interactions",
        json={"direction": "inbound", "summary": "sent a file listing"},
    )

    hits = client.get("/api/interactions", params={"q": "0.05 BTC"}).json()
    assert hits["total"] == 1
    assert hits["items"][0]["case_ref"] == "MSG-1"
    assert hits["items"][0]["case_title"] == "MSG-1"

    inbound = client.get("/api/interactions", params={"direction": "inbound"}).json()
    assert inbound["total"] == 1
    assert inbound["items"][0]["summary"] == "sent a file listing"
