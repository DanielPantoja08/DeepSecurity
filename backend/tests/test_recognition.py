"""Tests for POST /api/recognize — happy path and error cases."""
import io

from conftest import make_jpeg, mock_detector, mock_recognizer


# ── Happy path ────────────────────────────────────────────────────────────────

async def test_recognize_no_faces_detected(auth_client):
    """Valid image, detector returns no faces → 200 with empty list."""
    mock_detector.detect_faces.return_value = []

    resp = await auth_client.post(
        "/api/recognize",
        files={"file": ("frame.jpg", io.BytesIO(make_jpeg()), "image/jpeg")},
    )
    assert resp.status_code == 200
    assert resp.json() == {"faces": []}


async def test_recognize_with_detected_face(auth_client):
    """Detector returns one face → recognizer is called, result has one entry."""
    mock_detector.detect_faces.return_value = [
        {"confidence": 0.97, "box": [0, 0, 5, 5]}
    ]
    mock_recognizer.find_identity.return_value = ("Alice", 0.15)

    try:
        resp = await auth_client.post(
            "/api/recognize",
            files={"file": ("frame.jpg", io.BytesIO(make_jpeg(20, 20)), "image/jpeg")},
        )
        assert resp.status_code == 200
        faces = resp.json()["faces"]
        assert len(faces) == 1
        assert faces[0]["name"] == "Alice"
        assert "similarity" in faces[0]
        assert "box" in faces[0]
    finally:
        mock_detector.detect_faces.return_value = []
        mock_recognizer.find_identity.return_value = ("Unknown", 1.0)


async def test_recognize_low_confidence_face_filtered(auth_client):
    """Faces with detection confidence ≤ 0.9 are skipped."""
    mock_detector.detect_faces.return_value = [
        {"confidence": 0.85, "box": [0, 0, 5, 5]}
    ]
    try:
        resp = await auth_client.post(
            "/api/recognize",
            files={"file": ("frame.jpg", io.BytesIO(make_jpeg()), "image/jpeg")},
        )
        assert resp.status_code == 200
        assert resp.json()["faces"] == []
    finally:
        mock_detector.detect_faces.return_value = []


# ── Error cases ───────────────────────────────────────────────────────────────

async def test_recognize_file_too_large(auth_client):
    """Files larger than 10 MB are rejected with 413."""
    large_data = b"\xff\xd8\xff" + b"\x00" * (10 * 1024 * 1024 + 1)
    resp = await auth_client.post(
        "/api/recognize",
        files={"file": ("big.jpg", io.BytesIO(large_data), "image/jpeg")},
    )
    assert resp.status_code == 413


async def test_recognize_invalid_mime_type(auth_client):
    """Non-image bytes are rejected with 415."""
    resp = await auth_client.post(
        "/api/recognize",
        files={"file": ("file.txt", io.BytesIO(b"this is not an image"), "text/plain")},
    )
    assert resp.status_code == 415


async def test_recognize_requires_auth(client):
    resp = await client.post(
        "/api/recognize",
        files={"file": ("frame.jpg", io.BytesIO(make_jpeg()), "image/jpeg")},
    )
    assert resp.status_code == 401


async def test_recognize_png_accepted(auth_client):
    """PNG files (valid magic bytes) are accepted."""
    import cv2
    import numpy as np

    img = np.zeros((10, 10, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    png_data = buf.tobytes()

    mock_detector.detect_faces.return_value = []
    resp = await auth_client.post(
        "/api/recognize",
        files={"file": ("frame.png", io.BytesIO(png_data), "image/png")},
    )
    assert resp.status_code == 200
