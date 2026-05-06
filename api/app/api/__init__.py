"""API router exports."""
from app.api.auth import router as auth_router
from app.api.config import router as config_router
from app.api.metrics import router as metrics_router
from app.api.agents import router as agents_router
from app.api.alerts import router as alerts_router

__all__ = ["auth_router", "config_router", "metrics_router", "agents_router", "alerts_router"]
