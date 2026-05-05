"""
OC-Monitor v3.0 - API 初始化
"""
from app.api.metrics import router as metrics_router
from app.api.agents import router as agents_router
from app.api.alerts import router as alerts_router

__all__ = ["metrics_router", "agents_router", "alerts_router"]
