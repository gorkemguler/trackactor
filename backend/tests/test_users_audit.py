"""v0.4 - sessions, ownership, audit trail."""

import pytest

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.security import hash_password


@pytest.fixture
def user():
    db = SessionLocal()
    u = User(username="alice", password_hash=hash_password("hunter2"), is_admin=True)
    db.add(u)
    db.commit()
    db.close()
    return {"username": "alice", "password": "hunter2"}


@pytest.fixture
def require_login(monkeypatch):
    monkeypatch.setattr(settings, "require_login", True)


def test_login_me_logout(client, user):
    assert client.get("/api/auth/me").status_code == 401

    r = client.post("/api/auth/login", json=user)
    assert r.status_code == 200
    assert r.json()["username"] == "alice"
    assert client.cookies.get("trackactor_session")

    assert client.get("/api/auth/me").json()["username"] == "alice"

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_bad_password_rejected(client, user):
    assert client.post("/api/auth/login", json={"username": "alice", "password": "nope"}).status_code == 401


def test_session_gate(client, user, require_login):
    assert client.get("/api/cases").status_code == 401
    client.post("/api/auth/login", json=user)
    assert client.get("/api/cases").status_code == 200
    assert client.post("/api/cases", json={"case_id": "S-1", "title": "x"}).status_code == 201


def test_created_by_is_stamped(client, user):
    client.post("/api/auth/login", json=user)
    case = client.post("/api/cases", json={"case_id": "OWN-1", "title": "x"}).json()
    assert case["created_by"] == "alice"


def test_assignee_can_be_set(client, user):
    # need the user id
    users = client.get("/api/users").json()
    alice_id = next(u["id"] for u in users if u["username"] == "alice")
    case = client.post("/api/cases", json={"case_id": "ASG-1", "title": "x"}).json()
    r = client.patch(f"/api/cases/{case['id']}", json={"assignee_id": alice_id})
    assert r.json()["assignee"] == "alice"


def test_audit_trail_on_case(client):
    case = client.post("/api/cases", json={"case_id": "AUD-1", "title": "first"}).json()
    client.patch(f"/api/cases/{case['id']}", json={"status": "closed", "priority": "high"})
    client.delete(f"/api/cases/{case['id']}")

    events = client.get("/api/audit", params={"entity_type": "case", "entity_id": case["id"]}).json()
    actions = [e["action"] for e in events["items"]]
    assert actions == ["delete", "update", "create"]  # newest first

    upd = next(e for e in events["items"] if e["action"] == "update")
    assert upd["changes"]["status"] == ["open", "closed"]
    assert "priority" in upd["changes"]


def test_audit_records_anon_without_auth(client):
    client.post("/api/actors", json={"name": "ghost"})
    ev = client.get("/api/audit", params={"entity_type": "actor"}).json()["items"][0]
    assert ev["user_label"] == "anon"
    assert ev["action"] == "create"
