"""
OC-Monitor v3.0 - Agent API 测试
"""
import pytest
import sys
from pathlib import Path
import time
import sqlite3

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "api"))

from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    # 创建表
    conn = sqlite3.connect("data/monitor.db")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS agent_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            agent_name TEXT,
            status TEXT,
            memory_mb REAL,
            cpu_percent REAL,
            timestamp REAL NOT NULL,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT,
            is_resolved BOOLEAN DEFAULT 0,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    
    with TestClient(app) as c:
        yield c


class TestAgentAPI:
    """Agent API 测试"""
    
    def test_receive_agent_metric(self, client):
        """测试接收 Agent 指标"""
        response = client.post("/api/v1/agents/metrics", json={
            "agent_id": "dev-main",
            "agent_name": "Niko",
            "status": "online",
            "memory_mb": 75.5,
            "cpu_percent": 0.8,
            "timestamp": time.time()
        })
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_list_agents(self, client):
        """测试获取 Agent 列表"""
        # 先插入数据
        client.post("/api/v1/agents/metrics", json={
            "agent_id": "dev-backend",
            "agent_name": "Backend Agent",
            "status": "online",
            "memory_mb": 60.0,
            "cpu_percent": 0.5,
            "timestamp": time.time()
        })
        
        # 查询列表
        response = client.get("/api/v1/agents/list")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestAlertAPI:
    """告警 API 测试"""
    
    def test_create_alert(self, client):
        """测试创建告警"""
        response = client.post("/api/v1/alerts", json={
            "alert_type": "cpu",
            "severity": "warning",
            "title": "CPU 使用率过高",
            "message": "CPU 使用率达到 85%"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["alert_type"] == "cpu"
        assert data["severity"] == "warning"
        assert data["is_resolved"] == False
    
    def test_list_alerts(self, client):
        """测试获取告警列表"""
        response = client.get("/api/v1/alerts?is_resolved=false")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_resolve_alert(self, client):
        """测试解决告警"""
        # 先创建告警
        create_response = client.post("/api/v1/alerts", json={
            "alert_type": "memory",
            "severity": "critical",
            "title": "内存不足",
            "message": "内存使用率达到 95%"
        })
        alert_id = create_response.json()["id"]
        
        # 解决告警
        response = client.post(f"/api/v1/alerts/{alert_id}/resolve")
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_alert_stats(self, client):
        """测试告警统计"""
        response = client.get("/api/v1/alerts/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "unresolved" in data
        assert "today_count" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
