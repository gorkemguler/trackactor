"""v0.3 - outbound webhooks."""

import hashlib
import hmac
import json

import pytest

from app import events


class FakeResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code


@pytest.fixture
def sent(monkeypatch):
    """Capture every webhook POST instead of making a real request."""
    calls = []

    def fake_post(url, content, headers, timeout):
        calls.append({"url": url, "body": content, "headers": headers})
        return FakeResponse(200)

    monkeypatch.setattr(events.httpx, "post", fake_post)
    return calls


def _hook(client, events_list=None, url="https://sink.example/hook"):
    r = client.post(
        "/api/webhooks",
        json={"url": url, "secret": "whsec", "events": events_list or ["*"]},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_webhook_secret_is_never_returned(client):
    h = _hook(client)
    assert "secret" not in h
    assert client.get("/api/webhooks").json()[0].get("secret") is None


def test_unknown_event_rejected(client):
    r = client.post(
        "/api/webhooks", json={"url": "https://x.example", "secret": "s", "events": ["bogus"]}
    )
    assert r.status_code == 422


def test_inbound_interaction_fires_signed_webhook(client, sent):
    _hook(client, ["interaction.inbound"])
    case = client.post(
        "/api/cases", json={"case_id": "WH-1", "title": "x", "status": "awaiting_response"}
    ).json()
    client.post(
        f"/api/cases/{case['id']}/interactions",
        json={"direction": "inbound", "summary": "reply text"},
    )

    events_seen = [json.loads(c["body"])["event"] for c in sent]
    assert "interaction.inbound" in events_seen
    # awaiting_response -> responded also fires
    assert "case.status_changed" not in events_seen  # hook only subscribed to inbound

    call = next(c for c in sent if json.loads(c["body"])["event"] == "interaction.inbound")
    body = call["body"]
    expected = "sha256=" + hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    assert call["headers"]["x-trackactor-signature"] == expected
    assert json.loads(body)["data"]["case"]["case_id"] == "WH-1"


def test_event_filter_is_respected(client, sent):
    _hook(client, ["case.status_changed"])
    case = client.post("/api/cases", json={"case_id": "WH-2", "title": "x"}).json()
    client.post(
        f"/api/cases/{case['id']}/interactions",
        json={"direction": "outbound", "summary": "ping"},
    )
    client.patch(f"/api/cases/{case['id']}", json={"status": "closed"})

    seen = [json.loads(c["body"])["event"] for c in sent]
    assert seen == ["case.status_changed"]


def test_test_button_posts_a_ping(client, sent):
    h = _hook(client)
    r = client.post(f"/api/webhooks/{h['id']}/test").json()
    assert r["ok"] is True and r["status"] == 200
    assert json.loads(sent[-1]["body"])["event"] == "ping"
