"""v0.3 - API keys and the auth gate."""

import pytest

from app.config import settings


@pytest.fixture
def require_key(monkeypatch):
    monkeypatch.setattr(settings, "require_key", True)
    yield


def _make_key(client, scope="write", label="test"):
    r = client.post("/api/keys", json={"label": label, "scope": scope})
    assert r.status_code == 201, r.text
    return r.json()


def test_key_is_returned_once_then_hidden(client):
    created = _make_key(client)
    assert created["key"].startswith("tk_")
    assert created["prefix"] == created["key"][:12]

    listed = client.get("/api/keys").json()
    assert "key" not in listed[0]
    assert listed[0]["prefix"] == created["prefix"]


def test_gate_is_noop_by_default(client):
    # no require_key fixture -> everything open, no header needed
    assert client.get("/api/cases").status_code == 200
    assert client.post("/api/cases", json={"case_id": "OPEN-1", "title": "x"}).status_code == 201


def test_writes_need_a_write_key(client, require_key):
    read_key = _make_key(client, scope="read")["key"]
    write_key = _make_key(client, scope="write")["key"]

    # no key at all
    assert client.get("/api/cases").status_code == 401
    assert client.post("/api/cases", json={"case_id": "K-1", "title": "x"}).status_code == 401

    # read key: GET ok, POST forbidden
    assert client.get("/api/cases", headers={"X-API-Key": read_key}).status_code == 200
    r = client.post("/api/cases", json={"case_id": "K-1", "title": "x"}, headers={"X-API-Key": read_key})
    assert r.status_code == 403

    # write key: both ok
    assert (
        client.post(
            "/api/cases", json={"case_id": "K-2", "title": "x"}, headers={"X-API-Key": write_key}
        ).status_code
        == 201
    )


def test_revoked_key_is_rejected(client, require_key):
    k = _make_key(client)
    assert client.get("/api/cases", headers={"X-API-Key": k["key"]}).status_code == 200
    client.delete(f"/api/keys/{k['id']}")
    assert client.get("/api/cases", headers={"X-API-Key": k["key"]}).status_code == 401


def test_health_and_meta_stay_open(client, require_key):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/meta/enums").status_code == 200


def test_admin_token_guards_key_management(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "s3cret")
    assert client.get("/api/keys").status_code == 401
    assert client.get("/api/keys", headers={"X-Admin-Token": "s3cret"}).status_code == 200
