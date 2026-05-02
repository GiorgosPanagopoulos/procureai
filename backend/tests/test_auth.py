import pytest
from httpx import AsyncClient


def _get_cookie(response) -> str:
    for header in response.headers.multi_items():
        if header[0].lower() == "set-cookie" and "access_token=" in header[1]:
            parts = header[1].split(";")[0]  # "access_token=eyJ..."
            return parts.split("=", 1)[1]
    return ""


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, test_user: dict):
    res = await client.post("/auth/register", json=test_user)
    assert res.status_code == 200
    assert res.json()["email"] == test_user["email"]
    assert "access_token" in res.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient, test_user: dict):
    await client.post("/auth/register", json=test_user)
    res = await client.post("/auth/register", json=test_user)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: dict):
    await client.post("/auth/register", json=test_user)
    res = await client.post(
        "/auth/login",
        json={"email": test_user["email"], "password": test_user["password"]},
    )
    assert res.status_code == 200
    cookie_header = res.headers.get("set-cookie", "")
    assert "access_token" in cookie_header
    assert "httponly" in cookie_header.lower()


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: dict):
    await client.post("/auth/register", json=test_user)
    res = await client.post(
        "/auth/login",
        json={"email": test_user["email"], "password": "wrongpassword"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_with_cookie(client: AsyncClient, test_user: dict):
    reg_res = await client.post("/auth/register", json=test_user)
    token = _get_cookie(reg_res)
    me_res = await client.get("/auth/me", headers={"Cookie": f"access_token={token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == test_user["email"]


@pytest.mark.asyncio
async def test_me_without_cookie(client: AsyncClient):
    res = await client.get("/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_auth(client: AsyncClient):
    res = await client.get("/suppliers")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_auth(client: AsyncClient, test_user: dict):
    reg_res = await client.post("/auth/register", json=test_user)
    token = _get_cookie(reg_res)
    res = await client.get("/suppliers", headers={"Cookie": f"access_token={token}"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, test_user: dict):
    reg_res = await client.post("/auth/register", json=test_user)
    token = _get_cookie(reg_res)
    logout_res = await client.post(
        "/auth/logout", headers={"Cookie": f"access_token={token}"}
    )
    assert logout_res.status_code == 200
    cookie_header = logout_res.headers.get("set-cookie", "")
    assert "access_token" in cookie_header
    assert "max-age=0" in cookie_header.lower()
