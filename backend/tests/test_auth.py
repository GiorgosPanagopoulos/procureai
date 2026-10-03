from unittest.mock import patch

import pytest
from config import settings
from httpx import AsyncClient


def _get_cookie(response) -> str:
    for header in response.headers.multi_items():
        if header[0].lower() == "set-cookie" and "access_token=" in header[1]:
            parts = header[1].split(";")[0]  # "access_token=eyJ..."
            return parts.split("=", 1)[1]
    return ""


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client: AsyncClient, email: str, password: str):
    return await client.post("/auth/login", json={"email": email, "password": password})


# ── register (admin only) ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_unauthenticated_is_401(client: AsyncClient, test_user: dict):
    res = await client.post("/auth/register", json=test_user)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_register_as_viewer_is_403(client: AsyncClient, test_user: dict, make_user):
    _, token = await make_user("viewer")
    res = await client.post("/auth/register", json=test_user, headers=_bearer(token))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_register_as_procurement_officer_is_403(
    client: AsyncClient, test_user: dict, make_user
):
    _, token = await make_user("procurement_officer")
    res = await client.post("/auth/register", json=test_user, headers=_bearer(token))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_register_as_admin_is_201(client: AsyncClient, test_user: dict, make_user):
    _, token = await make_user("admin")
    res = await client.post("/auth/register", json=test_user, headers=_bearer(token))
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == test_user["email"]
    assert body["role"] == "viewer"
    assert "hashed_password" not in body
    # Must not overwrite the admin's own session with the new user's token.
    assert "access_token" not in res.headers.get("set-cookie", "")


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["admin", "procurement_officer", "viewer"])
async def test_register_admin_can_assign_role(
    client: AsyncClient, test_user: dict, make_user, role: str
):
    _, token = await make_user("admin")
    res = await client.post(
        "/auth/register", json={**test_user, "role": role}, headers=_bearer(token)
    )
    assert res.status_code == 201
    assert res.json()["role"] == role


@pytest.mark.asyncio
async def test_register_rejects_unknown_role(client: AsyncClient, test_user: dict, make_user):
    _, token = await make_user("admin")
    res = await client.post(
        "/auth/register", json={**test_user, "role": "superuser"}, headers=_bearer(token)
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient, test_user: dict, make_user):
    _, token = await make_user("admin")
    await client.post("/auth/register", json=test_user, headers=_bearer(token))
    res = await client.post("/auth/register", json=test_user, headers=_bearer(token))
    assert res.status_code == 400


# ── login ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_success_returns_token_and_cookie(client: AsyncClient, make_user):
    user, _ = await make_user("viewer")
    res = await _login(client, user["email"], "TestPass123!")
    assert res.status_code == 200
    body = res.json()
    assert body["message"] == "Login successful"
    assert body["user"]["email"] == user["email"]
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["access_token"] == _get_cookie(res)
    cookie_header = res.headers.get("set-cookie", "")
    assert "httponly" in cookie_header.lower()


@pytest.mark.asyncio
async def test_login_cookie_is_lax_locally(client: AsyncClient, make_user, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    user, _ = await make_user("viewer")
    cookie_header = (await _login(client, user["email"], "TestPass123!")).headers["set-cookie"]
    assert "samesite=lax" in cookie_header.lower()
    assert "secure" not in cookie_header.lower()


@pytest.mark.asyncio
async def test_login_cookie_is_cross_site_outside_local(
    client: AsyncClient, make_user, monkeypatch
):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    user, _ = await make_user("viewer")
    cookie_header = (await _login(client, user["email"], "TestPass123!")).headers["set-cookie"]
    assert "samesite=none" in cookie_header.lower()
    assert "secure" in cookie_header.lower()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, make_user):
    user, _ = await make_user("viewer")
    res = await _login(client, user["email"], "wrongpassword")
    assert res.status_code == 401


# ── token transport ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_me_with_bearer(client: AsyncClient, make_user):
    user, _ = await make_user("viewer")
    token = (await _login(client, user["email"], "TestPass123!")).json()["access_token"]
    client.cookies.clear()
    res = await client.get("/auth/me", headers=_bearer(token))
    assert res.status_code == 200
    assert res.json()["email"] == user["email"]


@pytest.mark.asyncio
async def test_me_with_cookie_fallback(client: AsyncClient, make_user):
    user, token = await make_user("viewer")
    res = await client.get("/auth/me", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 200
    assert res.json()["email"] == user["email"]


@pytest.mark.asyncio
async def test_bearer_takes_precedence_over_cookie(client: AsyncClient, make_user):
    _, viewer_token = await make_user("viewer")
    admin, admin_token = await make_user("admin")
    res = await client.get(
        "/auth/me",
        headers={**_bearer(admin_token), "Cookie": f"access_token={viewer_token}"},
    )
    assert res.status_code == 200
    assert res.json()["email"] == admin["email"]


@pytest.mark.asyncio
async def test_invalid_bearer_is_401(client: AsyncClient):
    res = await client.get("/auth/me", headers=_bearer("not-a-jwt"))
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_non_bearer_scheme_is_ignored(client: AsyncClient, make_user):
    _, token = await make_user("viewer")
    res = await client.get("/auth/me", headers={"Authorization": f"Basic {token}"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_without_credentials(client: AsyncClient):
    res = await client.get("/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_auth(client: AsyncClient):
    res = await client.get("/suppliers")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_bearer(client: AsyncClient, make_user):
    _, token = await make_user("viewer")
    res = await client.get("/suppliers", headers=_bearer(token))
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_protected_endpoint_with_cookie(client: AsyncClient, make_user):
    _, token = await make_user("viewer")
    res = await client.get("/suppliers", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, make_user):
    _, token = await make_user("viewer")
    logout_res = await client.post("/auth/logout", headers=_bearer(token))
    assert logout_res.status_code == 200
    cookie_header = logout_res.headers.get("set-cookie", "")
    assert "access_token" in cookie_header
    assert "max-age=0" in cookie_header.lower()


@pytest.mark.asyncio
async def test_login_does_not_create_new_mongo_client(client: AsyncClient, make_user):
    """Regression: auth handlers must reuse the db.py singleton, not open a fresh client."""
    user, _ = await make_user("viewer")

    with patch("motor.motor_asyncio.AsyncIOMotorClient") as mock_client:
        res = await _login(client, user["email"], "TestPass123!")

    assert res.status_code == 200
    assert mock_client.call_count == 0, (
        "AsyncIOMotorClient was instantiated during /auth/login — singleton not being reused"
    )
