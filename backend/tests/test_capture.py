def test_capture_creates_everything(client):
    r = client.post(
        "/api/capture",
        json={
            "case": {
                "case_id": "OPENCTI-2026-7001",
                "title": "IAB listing follow-up",
                "source_platform": "OpenCTI",
                "source_url": "https://opencti.local/cases/7001",
            },
            "actor": {"name": "broker_x", "actor_type": "initial_access_broker"},
            "contact": {"channel_type": "telegram", "value": "https://t.me/broker_x_deals"},
            "interaction": {"direction": "outbound", "summary": "Asked for target sector."},
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["created"] == {
        "case": True,
        "actor": True,
        "contact": True,
        "interaction": True,
    }
    case = body["case"]
    assert case["case_id"] == "OPENCTI-2026-7001"
    assert [a["name"] for a in case["actors"]] == ["broker_x"]
    assert case["contacts"][0]["normalized"] == "broker_x_deals"
    assert len(case["interactions"]) == 1


def test_capture_is_idempotent_on_case_and_actor(client):
    payload = {
        "case": {"case_id": "DUP-9", "title": "first"},
        "actor": {"name": "same_actor"},
        "contact": {"channel_type": "telegram", "value": "@same_actor_ch"},
    }
    first = client.post("/api/capture", json=payload).json()
    second = client.post("/api/capture", json=payload).json()

    assert first["created"]["case"] is True
    assert second["created"] == {
        "case": False,
        "actor": False,
        "contact": False,
        "interaction": False,
    }
    # still just one actor / one contact link on the case
    assert len(second["case"]["actors"]) == 1
    assert len(second["case"]["contacts"]) == 1


def test_capture_links_new_contact_to_existing_case(client):
    client.post("/api/cases", json={"case_id": "EXIST-1", "title": "already here"})
    r = client.post(
        "/api/capture",
        json={
            "case": {"case_id": "EXIST-1"},
            "contact": {"channel_type": "xmpp", "value": "dealer@jabber.ru"},
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["created"]["case"] is False
    assert body["created"]["contact"] is True
    assert body["case"]["contacts"][0]["value"] == "dealer@jabber.ru"


def test_capture_inbound_flips_awaiting_status(client):
    client.post(
        "/api/cases", json={"case_id": "FLIP-2", "title": "waiting", "status": "awaiting_response"}
    )
    client.post(
        "/api/capture",
        json={
            "case": {"case_id": "FLIP-2"},
            "interaction": {"direction": "inbound", "summary": "they answered"},
        },
    )
    assert client.get("/api/cases").json()  # sanity
    detail = client.get("/api/lookup", params={"q": "FLIP-2"}).json()
    assert detail["case_hits"][0]["status"] == "responded"
