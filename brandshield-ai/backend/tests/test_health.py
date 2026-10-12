import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.config import Settings


client = TestClient(app)


def test_process_health():
    """Verify /health returns 200 and process status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "brandshield-ai-backend"
    assert "environment" in data


def test_api_readiness_connected():
    """Verify /api/v1/health returns 200 when database ping succeeds."""
    with patch("app.main.ping_database", return_value=(True, "connected")):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert "database_name" in data


def test_api_readiness_disconnected():
    """Verify /api/v1/health returns 503 when database ping fails (no false readiness)."""
    with patch("app.main.ping_database", return_value=(False, "Database unreachable")):
        response = client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
        assert "Database unreachable" in data["detail"]


def test_safety_guard_rejects_matching_db_names():
    """Verify that Settings validation throws ValueError if test DB equals app DB."""
    with pytest.raises(ValueError, match="cannot be the same as DATABASE_NAME"):
        Settings(DATABASE_NAME="my_db", TEST_DATABASE_NAME="my_db")
