from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_login_success(client):
    response = await client.post("/api/admin/auth/login", json={"username": "admin", "password": "admin12345"})
    assert response.status_code == 200
    assert response.json()["admin"]["username"] == "admin"
    assert "admin_token" in response.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    response = await client.post("/api/admin/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    response = await client.get("/api/admin/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_cookie(client):
    await client.post("/api/admin/auth/login", json={"username": "admin", "password": "admin12345"})
    response = await client.get("/api/admin/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


@pytest.mark.asyncio
async def test_change_password(client):
    await client.post("/api/admin/auth/login", json={"username": "admin", "password": "admin12345"})
    response = await client.post(
        "/api/admin/auth/change-password",
        json={"current_password": "admin12345", "new_password": "newpassword123"},
    )
    assert response.status_code == 200
    # login with new password
    response = await client.post("/api/admin/auth/login", json={"username": "admin", "password": "newpassword123"})
    assert response.status_code == 200
    # restore original password so other tests are not affected
    response = await client.post(
        "/api/admin/auth/change-password",
        json={"current_password": "newpassword123", "new_password": "admin12345"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_login_rate_limit(client):
    for _ in range(15):
        await client.post("/api/admin/auth/login", json={"username": "admin", "password": "wrongpass1"})
    response = await client.post("/api/admin/auth/login", json={"username": "admin", "password": "wrongpass1"})
    assert response.status_code == 429
