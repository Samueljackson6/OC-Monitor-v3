"""Integration tests for agent metrics and alerts."""
import os
import sys
import time
from pathlib import Path
import pytest

TEST_DB_PATH = Path("data/test_monitor.db").resolve()
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["INITIAL_ADMIN_PASSWORD"] = "test-admin-password"
os.environ["INGEST_TOKEN"] = "test-ingest-token"

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api"))

from fastapi.testclient import TestClient
from app.main import app


INGEST_HEADERS = {"x-oc-monitor-token": "test-ingest-token"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "test-admin-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


class TestAgentAPI:
    def test_receive_agent_metric_requires_ingest_token(self, client):
        payload = {
            "agent_id": "dev-main",
            "agent_name": "Niko",
            "status": "online",
            "memory_mb": 75.5,
            "cpu_percent": 0.8,
            "timestamp": time.time(),
        }
        assert client.post("/api/v1/agents/metrics", json=payload).status_code == 401
        response = client.post("/api/v1/agents/metrics", json=payload, headers=INGEST_HEADERS)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_list_agents(self, client):
        response = client.get("/api/v1/agents/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(agent["agent_id"] == "dev-main" for agent in data)


class TestAlertAPI:
    def test_create_alert_requires_ingest_token(self, client):
        payload = {
            "alert_type": "cpu",
            "severity": "warning",
            "title": "CPU high",
            "message": "CPU reached threshold",
        }
        assert client.post("/api/v1/alerts", json=payload).status_code == 401
        response = client.post("/api/v1/alerts", json=payload, headers=INGEST_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["alert_type"] == "cpu"
        assert data["is_resolved"] is False

    def test_list_alerts(self, client):
        response = client.get("/api/v1/alerts?is_resolved=false")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_resolve_alert_requires_admin(self, client):
        create_response = client.post(
            "/api/v1/alerts",
            json={"alert_type": "memory", "severity": "critical", "title": "Memory high"},
            headers=INGEST_HEADERS,
        )
        alert_id = create_response.json()["id"]
        assert client.post(f"/api/v1/alerts/{alert_id}/resolve").status_code == 401
        response = client.post(f"/api/v1/alerts/{alert_id}/resolve", headers=auth_headers(client))
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_alert_stats(self, client):
        response = client.get("/api/v1/alerts/stats")
        assert response.status_code == 200
        data = response.json()
        assert "unresolved" in data
        assert "today_count" in data
