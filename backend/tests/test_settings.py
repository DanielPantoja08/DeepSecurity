"""Tests for GET/POST /api/settings."""
import tempfile


# ── GET /api/settings ─────────────────────────────────────────────────────────

async def test_get_settings(auth_client):
    resp = await auth_client.get("/api/settings")
    assert resp.status_code == 200
    assert "db_path" in resp.json()


async def test_get_settings_requires_auth(client):
    resp = await client.get("/api/settings")
    assert resp.status_code == 401


# ── POST /api/settings ────────────────────────────────────────────────────────

async def test_update_settings_empty_path(auth_client):
    resp = await auth_client.post("/api/settings", json={"db_path": ""})
    assert resp.status_code == 400


async def test_update_settings_whitespace_path(auth_client):
    resp = await auth_client.post("/api/settings", json={"db_path": "   "})
    assert resp.status_code == 400


async def test_update_settings_valid_path(auth_client):
    with tempfile.TemporaryDirectory() as tmpdir:
        resp = await auth_client.post("/api/settings", json={"db_path": tmpdir})
        assert resp.status_code == 200
        data = resp.json()
        assert data["db_path"] == tmpdir


async def test_update_settings_creates_missing_dir(auth_client):
    """Settings endpoint creates the directory if it doesn't exist yet."""
    import os
    with tempfile.TemporaryDirectory() as parent:
        new_dir = os.path.join(parent, "new_subdir")
        assert not os.path.exists(new_dir)
        resp = await auth_client.post("/api/settings", json={"db_path": new_dir})
        assert resp.status_code == 200
        assert os.path.isdir(new_dir)


async def test_update_settings_requires_auth(client):
    resp = await client.post("/api/settings", json={"db_path": "/tmp"})
    assert resp.status_code == 401


async def test_update_settings_missing_field(auth_client):
    resp = await auth_client.post("/api/settings", json={})
    assert resp.status_code == 422


# ── POST /api/settings/browse ─────────────────────────────────────────────────

async def test_browse_disabled_in_docker(auth_client):
    """In test/Docker environment DISABLE_NATIVE_FILE_PICKER=true → 501."""
    import os
    os.environ["DISABLE_NATIVE_FILE_PICKER"] = "true"
    resp = await auth_client.post("/api/settings/browse")
    assert resp.status_code == 501


async def test_browse_requires_auth(client):
    resp = await client.post("/api/settings/browse")
    assert resp.status_code == 401
