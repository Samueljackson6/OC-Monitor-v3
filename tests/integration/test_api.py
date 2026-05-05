"""
OC-Monitor v3.0 - API 测试（简化版）
使用内存数据库
"""
import pytest
import sys
from pathlib import Path
import time

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api"))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 使用同步 SQLite 内存数据库测试
from app.models import Base
from app.main import app


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    # 创建内存数据库
    from app.database import engine
    
    # 同步创建表
    import sqlite3
    conn = sqlite3.connect("data/monitor.db")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS server_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpu REAL NOT NULL,
            memory REAL NOT NULL,
            disk REAL NOT NULL,
            gateway_status BOOLEAN DEFAULT 0,
            timestamp REAL NOT NULL,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    
    with TestClient(app) as c:
        yield c


class TestMetricsAPI:
    """指标 API 测试"""
    
    def test_root(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "OC-Monitor"
        assert data["version"] == "3.0.0"
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/v1/metrics/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestAPIDocs:
    """API 文档测试"""
    
    def test_swagger_docs(self, client):
        """测试 Swagger 文档"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_redoc(self, client):
        """测试 ReDoc"""
        response = client.get("/redoc")
        assert response.status_code == 200
    
    def test_openapi_json(self, client):
        """测试 OpenAPI JSON"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
