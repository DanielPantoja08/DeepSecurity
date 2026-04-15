"""Tests for identity (faces) CRUD — POST, GET, DELETE /api/faces."""
import io
import pathlib

from conftest import FACES_DIR, make_jpeg


# ── GET /api/faces ────────────────────────────────────────────────────────────

async def test_list_faces_returns_list(auth_client):
    resp = await auth_client.get("/api/faces")
    assert resp.status_code == 200
    assert "faces" in resp.json()


async def test_list_faces_requires_auth(client):
    resp = await client.get("/api/faces")
    assert resp.status_code == 401


# ── POST /api/faces/{name} ────────────────────────────────────────────────────

async def test_create_identity(auth_client):
    jpeg = make_jpeg()
    resp = await auth_client.post(
        "/api/faces/TestPerson",
        files={"files": ("face.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["saved"] == 1
    # Clean up
    person_dir = FACES_DIR / "TestPerson"
    if person_dir.exists():
        import shutil
        shutil.rmtree(person_dir)


async def test_create_identity_requires_auth(client):
    jpeg = make_jpeg()
    resp = await client.post(
        "/api/faces/Someone",
        files={"files": ("face.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 401


async def test_create_identity_path_traversal_dots(auth_client):
    jpeg = make_jpeg()
    resp = await auth_client.post(
        "/api/faces/..%2Fetc%2Fpasswd",
        files={"files": ("f.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    # FastAPI decodes %2F → / which splits the path segment, yielding 404 or 400
    assert resp.status_code in (400, 404, 422)


async def test_create_identity_invalid_name_special_chars(auth_client):
    jpeg = make_jpeg()
    resp = await auth_client.post(
        "/api/faces/name;rm+-rf",
        files={"files": ("f.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 400


async def test_create_identity_name_too_long(auth_client):
    jpeg = make_jpeg()
    long_name = "A" * 65
    resp = await auth_client.post(
        f"/api/faces/{long_name}",
        files={"files": ("f.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    assert resp.status_code == 400


async def test_create_multiple_files(auth_client):
    jpeg = make_jpeg()
    resp = await auth_client.post(
        "/api/faces/MultiFileTest",
        files=[
            ("files", ("a.jpg", io.BytesIO(jpeg), "image/jpeg")),
            ("files", ("b.jpg", io.BytesIO(jpeg), "image/jpeg")),
        ],
    )
    assert resp.status_code == 201
    assert resp.json()["saved"] == 2
    # Clean up
    import shutil
    person_dir = FACES_DIR / "MultiFileTest"
    if person_dir.exists():
        shutil.rmtree(person_dir)


# ── DELETE /api/faces/{name} ──────────────────────────────────────────────────

async def test_delete_identity_not_found(auth_client):
    resp = await auth_client.delete("/api/faces/PersonThatDoesNotExist")
    assert resp.status_code == 404


async def test_delete_identity_success(auth_client):
    # Create first
    jpeg = make_jpeg()
    await auth_client.post(
        "/api/faces/ToDelete",
        files={"files": ("f.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    # Then delete
    resp = await auth_client.delete("/api/faces/ToDelete")
    assert resp.status_code == 204
    # Verify dir is gone
    assert not (FACES_DIR / "ToDelete").exists()


async def test_delete_identity_requires_auth(client):
    resp = await client.delete("/api/faces/Someone")
    assert resp.status_code == 401


async def test_delete_identity_invalid_name(auth_client):
    resp = await auth_client.delete("/api/faces/../../etc")
    assert resp.status_code in (400, 404, 422)
