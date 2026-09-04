"""v0.3 - API keys and the auth gate."""

import pytest

from app.config import settings


@pytest.fixture
def require_key(monkeypatch):
    # a locked API also needs an admin token to reach key management
    monkeypatch.setattr(settings, "require_key", True)
    monkeypatch.setattr(settings, "admin_token", "test-admin")
    yield


ADMIN = {"X-Admin-Token": "test-admin"}


def _make_key(client, scope="write", label="test", admin=False):
    headers = ADMIN if admin else {}
    r = client.post("/api/keys", json={"label": label, "scope": scope}, headers=headers)
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
    read_key = _make_key(client, scope="read", admin=True)["key"]
    write_key = _make_key(client, scope="write", admin=True)["key"]

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
    k = _make_key(client, admin=True)
    assert client.get("/api/cases", headers={"X-API-Key": k["key"]}).status_code == 200
    client.delete(f"/api/keys/{k['id']}", headers=ADMIN)
    assert client.get("/api/cases", headers={"X-API-Key": k["key"]}).status_code == 401


def test_key_management_needs_admin_when_api_is_locked(client, monkeypatch):
    # require_key on, no admin token configured -> key routes are closed
    monkeypatch.setattr(settings, "require_key", True)
    assert client.post("/api/keys", json={"label": "x", "scope": "read"}).status_code == 401


def test_admin_session_can_manage_keys(client, monkeypatch):
    monkeypatch.setattr(settings, "require_login", True)  # API locked, no admin token
    from app.database import SessionLocal
    from app.models import User
    from app.security import hash_password

    db = SessionLocal()
    db.add(User(username="boss", password_hash=hash_password("pw123456"), is_admin=True))
    db.add(User(username="peon", password_hash=hash_password("pw123456"), is_admin=False))
    db.commit()
    db.close()

    client.post("/api/auth/login", json={"username": "peon", "password": "pw123456"})
    assert client.post("/api/keys", json={"label": "x", "scope": "read"}).status_code == 401
    client.post("/api/auth/login", json={"username": "boss", "password": "pw123456"})
    assert client.post("/api/keys", json={"label": "x", "scope": "read"}).status_code == 201


def test_health_and_meta_stay_open(client, require_key):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/meta/enums").status_code == 200


def test_admin_token_guards_key_management(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "s3cret")
    assert client.get("/api/keys").status_code == 401
    assert client.get("/api/keys", headers={"X-Admin-Token": "s3cret"}).status_code == 200
