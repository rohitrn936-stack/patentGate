"""Every resource route must enforce auth AND per-user data isolation."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

PROTECTED = [
    ("get", "/api/products"),
    ("post", "/api/products"),
    ("get", "/api/analyses"),
    ("post", "/api/analyses"),
    ("post", "/api/agent1"),
]


@pytest.mark.parametrize("method,path", PROTECTED)
async def test_routes_reject_anonymous(client, method, path):
    kwargs = {"json": {}} if method == "post" else {}
    resp = await getattr(client, method)(path, **kwargs)
    assert resp.status_code == 401, f"{method} {path} should require auth"


async def _register(client, email):
    r = await client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    return r.json()["access_token"]


async def test_user_cannot_read_another_users_product(client):
    alice = await _register(client, "alice@example.com")
    bob = await _register(client, "bob@example.com")

    made = await client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {alice}"},
        json={"name": "Alice widget", "description": "secret design"},
    )
    assert made.status_code == 201
    product_id = made.json()["id"]

    # Bob cannot see it in his list...
    bob_list = await client.get("/api/products", headers={"Authorization": f"Bearer {bob}"})
    assert bob_list.json() == []

    # ...nor fetch it directly (404, not 403 - don't leak existence).
    direct = await client.get(
        f"/api/products/{product_id}", headers={"Authorization": f"Bearer {bob}"}
    )
    assert direct.status_code == 404

    # ...nor delete it.
    deleted = await client.delete(
        f"/api/products/{product_id}", headers={"Authorization": f"Bearer {bob}"}
    )
    assert deleted.status_code == 404


async def test_user_cannot_run_or_read_another_users_analysis(client):
    alice = await _register(client, "a2@example.com")
    bob = await _register(client, "b2@example.com")
    ah = {"Authorization": f"Bearer {alice}"}
    bh = {"Authorization": f"Bearer {bob}"}

    product = (
        await client.post("/api/products", headers=ah, json={"name": "P", "description": "d"})
    ).json()
    analysis = (
        await client.post("/api/analyses", headers=ah, json={"product_id": product["id"]})
    ).json()

    assert (await client.get(f"/api/analyses/{analysis['id']}", headers=bh)).status_code == 404
    assert (
        await client.post(f"/api/analyses/{analysis['id']}/run", headers=bh)
    ).status_code == 404


async def test_cannot_create_analysis_for_someone_elses_product(client):
    alice = await _register(client, "a3@example.com")
    bob = await _register(client, "b3@example.com")
    product = (
        await client.post(
            "/api/products",
            headers={"Authorization": f"Bearer {alice}"},
            json={"name": "P", "description": "d"},
        )
    ).json()

    resp = await client.post(
        "/api/analyses",
        headers={"Authorization": f"Bearer {bob}"},
        json={"product_id": product["id"]},
    )
    assert resp.status_code == 404


async def test_image_url_scheme_is_validated(auth_client):
    client, _ = auth_client
    resp = await client.post(
        "/api/products",
        json={"name": "x", "description": "d", "image_url": "javascript:alert(1)"},
    )
    assert resp.status_code == 422
