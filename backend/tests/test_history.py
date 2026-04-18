"""Tests for /api/history — logs, recordings, download tokens."""


# ── GET /api/history/logs ─────────────────────────────────────────────────────

async def test_get_logs_empty(auth_client):
    resp = await auth_client.get("/api/history/logs")
    assert resp.status_code == 200
    assert isinstance(resp.json()["items"], list)


async def test_get_logs_requires_auth(client):
    resp = await client.get("/api/history/logs")
    assert resp.status_code == 401


async def test_get_logs_limit_param(auth_client):
    resp = await auth_client.get("/api/history/logs?limit=5")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) <= 5


async def test_get_logs_invalid_limit(auth_client):
    """Non-integer limit is a validation error."""
    resp = await auth_client.get("/api/history/logs?limit=notanumber")
    assert resp.status_code == 422


# ── GET /api/history/recordings ───────────────────────────────────────────────

async def test_get_recordings_empty(auth_client):
    resp = await auth_client.get("/api/history/recordings")
    assert resp.status_code == 200
    assert isinstance(resp.json()["items"], list)


async def test_get_recordings_requires_auth(client):
    resp = await client.get("/api/history/recordings")
    assert resp.status_code == 401


# ── POST /api/history/recordings/{id}/download-token ─────────────────────────

async def test_download_token_not_found(auth_client):
    resp = await auth_client.post("/api/history/recordings/99999/download-token")
    assert resp.status_code == 404


async def test_download_token_requires_auth(client):
    resp = await client.post("/api/history/recordings/1/download-token")
    assert resp.status_code == 401


# ── GET /api/history/recordings/{id}/file ────────────────────────────────────

async def test_get_recording_file_missing_token(client):
    """No download_token param → 401."""
    resp = await client.get("/api/history/recordings/1/file")
    assert resp.status_code == 401


async def test_get_recording_file_invalid_token(client):
    """Invalid download_token → 401."""
    resp = await client.get(
        "/api/history/recordings/1/file?download_token=invalid-token-xyz"
    )
    assert resp.status_code == 401
