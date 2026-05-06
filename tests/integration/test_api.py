"""Integration tests for core API behavior."""
import os
import sys
import time
from pathlib import Path
import pytest

TEST_DB_PATH = Path("data/test_monitor.db").resolve()
TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
TEST_DB_PATH.unlink(missing_ok=True)

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


class TestCoreAPI:
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "OC-Monitor"
        assert data["version"] == "3.0.0"

    def test_health_check(self, client):
        response = client.get("/api/v1/metrics/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_ingest_token_required_for_metric_write(self, client):
        payload = {"metrics": [{"cpu": 10, "memory": 20, "disk": 30, "gateway_status": True, "timestamp": time.time()}]}
        unauthorized = client.post("/api/v1/metrics/batch", json=payload)
        assert unauthorized.status_code == 401
        authorized = client.post("/api/v1/metrics/batch", json=payload, headers=INGEST_HEADERS)
        assert authorized.status_code == 200
        assert authorized.json()["received"] == 1

    def test_realtime_after_ingest(self, client):
        response = client.get("/api/v1/metrics/realtime")
        assert response.status_code == 200
        data = response.json()
        assert data["cpu"] == 10
        assert data["gateway_status"] is True

    def test_auth_and_protected_config(self, client):
        assert client.get("/api/v1/config").status_code == 401
        response = client.get("/api/v1/config", headers=auth_headers(client))
        assert response.status_code == 200
        assert "data_retention_days" in response.json()

    def test_public_stats_and_runtime(self, client):
        assert client.get("/api/v1/config/runtime").status_code == 200
        response = client.get("/api/v1/config/stats")
        assert response.status_code == 200
        assert response.json()["server_metrics"] >= 1


class TestAPIDocs:
    def test_swagger_docs(self, client):
        assert client.get("/docs").status_code == 200

    def test_redoc(self, client):
        assert client.get("/redoc").status_code == 200

    def test_openapi_json(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert "paths" in response.json()
