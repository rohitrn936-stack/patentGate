from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_register_returns_tokens_and_user(client):
    resp = await client.post(
        "/api/auth/register",
        json={"name": "Grace", "email": "grace@example.com", "password": "hunter2pass"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    assert body["user"]["email"] == "grace@example.com"
    assert "password" not in body["user"] and "password_hash" not in body["user"]


async def test_register_rejects_weak_password(client):
    resp = await client.post(
        "/api/auth/register",
        json={"email": "weak@example.com", "password": "password"},  # no digit
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_register_duplicate_email_conflicts(client):
    payload = {"email": "dupe@example.com", "password": "password123"}
    assert (await client.post("/api/auth/register", json=payload)).status_code == 201
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


async def test_login_success_and_wrong_password(client):
    await client.post(
        "/api/auth/register",
        json={"email": "log@example.com", "password": "password123"},
    )
    ok = await client.post(
        "/api/auth/login", json={"email": "log@example.com", "password": "password123"}
    )
    assert ok.status_code == 200 and ok.json()["access_token"]

    bad = await client.post(
        "/api/auth/login", json={"email": "log@example.com", "password": "wrongpass1"}
    )
    assert bad.status_code == 401
    # Same generic message whether or not the account exists.
    missing = await client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "whatever12"}
    )
    assert missing.status_code == 401
    assert bad.json()["error"]["message"] == missing.json()["error"]["message"]


async def test_me_requires_bearer_token(client):
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_refresh_issues_new_access_token(client):
    reg = await client.post(
        "/api/auth/register", json={"email": "r@example.com", "password": "password123"}
    )
    refresh_token = reg.json()["refresh_token"]
    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_access_token_cannot_be_used_as_refresh_token(client):
    reg = await client.post(
        "/api/auth/register", json={"email": "x@example.com", "password": "password123"}
    )
    access = reg.json()["access_token"]
    resp = await client.post("/api/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401


async def test_logout_everywhere_invalidates_existing_tokens(client):
    reg = await client.post(
        "/api/auth/register", json={"email": "out@example.com", "password": "password123"}
    )
    access = reg.json()["access_token"]
    refresh = reg.json()["refresh_token"]
    client.headers["Authorization"] = f"Bearer {access}"

    assert (await client.get("/api/auth/me")).status_code == 200
    assert (await client.post("/api/auth/logout")).status_code == 204

    # Old access + refresh tokens are now rejected.
    assert (await client.get("/api/auth/me")).status_code == 401
    assert (
        await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    ).status_code == 401


async def test_garbage_token_is_rejected(client):
    client.headers["Authorization"] = "Bearer not-a-real-token"
    assert (await client.get("/api/auth/me")).status_code == 401
