"""Health check and app-level tests."""


async def test_health(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_app_instance():
    from backend.main import app
    assert app is not None


async def test_openapi_schema_available(client):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    assert "paths" in resp.json()
