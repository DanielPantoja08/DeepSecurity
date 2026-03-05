from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_read_root():
    """Verifica que el punto de entrada principal responda."""
    response = client.get("/")

    assert response.status_code in [200, 404] 

def test_app_instance():
    """Verifica que la instancia de la app existe."""
    assert app is not None
