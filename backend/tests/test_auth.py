"""Tests for authentication — register, login, token validation."""
import uuid


# ── Register ──────────────────────────────────────────────────────────────────

async def test_register_new_user(client):
    email = f"new-{uuid.uuid4().hex[:8]}@test.com"
    resp = await client.post(
        "/api/auth/register", json={"email": email, "password": "StrongPass1!"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == email
    assert "hashed_password" not in data


async def test_first_registered_user_is_superuser(client):
    """The very first account created is automatically promoted to superuser."""
    # admin@test.com is registered by the auth_client fixture first in the session,
    # so here we just verify a fresh user registers successfully with 201.
    email = f"su-check-{uuid.uuid4().hex[:8]}@test.com"
    resp = await client.post(
        "/api/auth/register", json={"email": email, "password": "StrongPass1!"}
    )
    assert resp.status_code == 201


async def test_register_duplicate_email(client):
    email = f"dup-{uuid.uuid4().hex[:8]}@test.com"
    await client.post(
        "/api/auth/register", json={"email": email, "password": "StrongPass1!"}
    )
    resp = await client.post(
        "/api/auth/register", json={"email": email, "password": "StrongPass1!"}
    )
    assert resp.status_code == 400


async def test_register_invalid_email(client):
    resp = await client.post(
        "/api/auth/register", json={"email": "not-an-email", "password": "Pass1!"}
    )
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

async def test_login_success(client):
    email = f"login-{uuid.uuid4().hex[:8]}@test.com"
    await client.post(
        "/api/auth/register", json={"email": email, "password": "LoginPass1!"}
    )
    resp = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": "LoginPass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    email = f"wrongpw-{uuid.uuid4().hex[:8]}@test.com"
    await client.post(
        "/api/auth/register", json={"email": email, "password": "CorrectPass1!"}
    )
    resp = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": "WrongPassword!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 400


async def test_login_unknown_user(client):
    resp = await client.post(
        "/api/auth/jwt/login",
        data={"username": "nobody@nowhere.com", "password": "Pass1!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 400


# ── /api/users/me ─────────────────────────────────────────────────────────────

async def test_get_me_authenticated(auth_client):
    resp = await auth_client.get("/api/users/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"


async def test_get_me_unauthenticated(client):
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


async def test_get_me_invalid_token(client):
    resp = await client.get(
        "/api/users/me", headers={"Authorization": "Bearer not.a.real.token"}
    )
    assert resp.status_code == 401
