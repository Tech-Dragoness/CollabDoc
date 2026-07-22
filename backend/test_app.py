"""
Automated tests for the document app backend.

Run with:
    cd backend
    pytest -v

These tests spin up the Flask app against an in-memory SQLite database
(swapped in via DATABASE_URL before the app is imported) so they run fast
and don't require a real Postgres instance. The app's models/queries are
plain SQLAlchemy so they work the same against SQLite for test purposes.
"""
import os
import io

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "a_super_secret_test_key_32_bytes_long"

import pytest
from app import create_app
from models import db


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()


def signup(client, email="alice@example.com", password="Passw0rd!23"):
    return client.post("/api/auth/signup", json={"email": email, "password": password})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- auth ----------

def test_signup_rejects_weak_password(client):
    resp = client.post("/api/auth/signup", json={"email": "a@b.com", "password": "weak"})
    assert resp.status_code == 400


def test_signup_and_login(client):
    resp = signup(client)
    assert resp.status_code == 201
    token = resp.get_json()["token"]

    resp = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "Passw0rd!23"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["token"]


def test_signup_duplicate_email_rejected(client):
    signup(client)
    resp = signup(client)
    assert resp.status_code == 409


# ---------- documents ----------

def test_create_and_fetch_document(client):
    token = signup(client).get_json()["token"]
    resp = client.post(
        "/api/documents", json={"title": "My Doc", "content": "<p>hello</p>"},
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    doc_id = resp.get_json()["id"]

    resp = client.get(f"/api/documents/{doc_id}", headers=auth_header(token))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "My Doc"
    assert body["is_owner"] is True


def test_document_persists_after_update(client):
    token = signup(client).get_json()["token"]
    doc_id = client.post(
        "/api/documents", json={"title": "Draft"}, headers=auth_header(token)
    ).get_json()["id"]

    client.put(
        f"/api/documents/{doc_id}",
        json={"content": "<p>updated body</p>"},
        headers=auth_header(token),
    )
    resp = client.get(f"/api/documents/{doc_id}", headers=auth_header(token))
    assert resp.get_json()["content"] == "<p>updated body</p>"


def test_txt_upload_creates_document(client):
    token = signup(client).get_json()["token"]
    data = {"file": (io.BytesIO(b"line one\nline two"), "notes.txt")}
    resp = client.post(
        "/api/documents", data=data, headers=auth_header(token),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    assert "line one" in resp.get_json()["content"]


# ---------- sharing ----------

def test_share_document_gives_access(client):
    owner_token = signup(client, "owner@example.com").get_json()["token"]
    signup(client, "friend@example.com")

    doc_id = client.post(
        "/api/documents", json={"title": "Shared Doc"}, headers=auth_header(owner_token)
    ).get_json()["id"]

    resp = client.post(
        f"/api/documents/{doc_id}/share",
        json={"email": "friend@example.com"},
        headers=auth_header(owner_token),
    )
    assert resp.status_code == 201

    friend_token = client.post(
        "/api/auth/login", json={"email": "friend@example.com", "password": "Passw0rd!23"}
    ).get_json()["token"]

    resp = client.get("/api/documents", headers=auth_header(friend_token))
    body = resp.get_json()
    assert len(body["shared"]) == 1
    assert body["shared"][0]["title"] == "Shared Doc"
    assert len(body["owned"]) == 0


def test_non_owner_cannot_delete(client):
    owner_token = signup(client, "owner2@example.com").get_json()["token"]
    signup(client, "friend2@example.com")
    doc_id = client.post(
        "/api/documents", json={"title": "X"}, headers=auth_header(owner_token)
    ).get_json()["id"]
    client.post(
        f"/api/documents/{doc_id}/share",
        json={"email": "friend2@example.com"},
        headers=auth_header(owner_token),
    )
    friend_token = client.post(
        "/api/auth/login", json={"email": "friend2@example.com", "password": "Passw0rd!23"}
    ).get_json()["token"]

    resp = client.delete(f"/api/documents/{doc_id}", headers=auth_header(friend_token))
    assert resp.status_code == 403


# ---------- new: permission editing, comments, collaborator ----------

def test_share_permission_can_be_updated(client):
    owner_token = signup(client, "owner3@example.com").get_json()["token"]
    signup(client, "friend3@example.com")
    doc_id = client.post(
        "/api/documents", json={"title": "X"}, headers=auth_header(owner_token)
    ).get_json()["id"]
    client.post(
        f"/api/documents/{doc_id}/share",
        json={"email": "friend3@example.com", "permission": "view"},
        headers=auth_header(owner_token),
    )
    shares = client.get(f"/api/documents/{doc_id}/shares", headers=auth_header(owner_token)).get_json()
    target_id = shares[0]["user_id"]

    resp = client.patch(
        f"/api/documents/{doc_id}/share/{target_id}",
        json={"permission": "comment"},
        headers=auth_header(owner_token),
    )
    assert resp.status_code == 200
    assert resp.get_json()["permission"] == "comment"


def test_comment_only_user_cannot_edit_but_can_comment(client):
    owner_token = signup(client, "owner4@example.com").get_json()["token"]
    signup(client, "friend4@example.com")
    doc_id = client.post(
        "/api/documents", json={"title": "X"}, headers=auth_header(owner_token)
    ).get_json()["id"]
    client.post(
        f"/api/documents/{doc_id}/share",
        json={"email": "friend4@example.com", "permission": "comment"},
        headers=auth_header(owner_token),
    )
    friend_token = client.post(
        "/api/auth/login", json={"email": "friend4@example.com", "password": "Passw0rd!23"}
    ).get_json()["token"]

    resp = client.put(
        f"/api/documents/{doc_id}", json={"content": "hack"}, headers=auth_header(friend_token)
    )
    assert resp.status_code == 403

    resp = client.post(
        f"/api/documents/{doc_id}/comments", json={"content": "nice doc"},
        headers=auth_header(friend_token),
    )
    assert resp.status_code == 201


def test_view_only_user_cannot_comment(client):
    owner_token = signup(client, "owner5@example.com").get_json()["token"]
    signup(client, "friend5@example.com")
    doc_id = client.post(
        "/api/documents", json={"title": "X"}, headers=auth_header(owner_token)
    ).get_json()["id"]
    client.post(
        f"/api/documents/{doc_id}/share",
        json={"email": "friend5@example.com", "permission": "view"},
        headers=auth_header(owner_token),
    )
    friend_token = client.post(
        "/api/auth/login", json={"email": "friend5@example.com", "password": "Passw0rd!23"}
    ).get_json()["token"]
    resp = client.post(
        f"/api/documents/{doc_id}/comments", json={"content": "nope"},
        headers=auth_header(friend_token),
    )
    assert resp.status_code == 403


def test_collaborator_has_full_rights_like_owner(client):
    owner_token = signup(client, "owner6@example.com").get_json()["token"]
    signup(client, "friend6@example.com")
    doc_id = client.post(
        "/api/documents", json={"title": "X"}, headers=auth_header(owner_token)
    ).get_json()["id"]
    client.post(
        f"/api/documents/{doc_id}/share",
        json={"email": "friend6@example.com", "permission": "collaborator"},
        headers=auth_header(owner_token),
    )
    friend_token = client.post(
        "/api/auth/login", json={"email": "friend6@example.com", "password": "Passw0rd!23"}
    ).get_json()["token"]

    resp = client.get(f"/api/documents/{doc_id}/access-log", headers=auth_header(friend_token))
    assert resp.status_code == 200

    resp = client.delete(f"/api/documents/{doc_id}", headers=auth_header(friend_token))
    assert resp.status_code == 200