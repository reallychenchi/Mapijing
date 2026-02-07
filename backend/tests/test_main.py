import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_get_config(client: TestClient) -> None:
    """Test get config endpoint."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "emotion_types" in data
    assert len(data["emotion_types"]) == 4
    assert "默认陪伴" in data["emotion_types"]
    assert "共情倾听" in data["emotion_types"]
    assert "安慰支持" in data["emotion_types"]
    assert "轻松愉悦" in data["emotion_types"]
