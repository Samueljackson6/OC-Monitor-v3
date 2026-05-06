"""Runtime configuration API."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import User, get_current_active_user
from app.config import settings
from app.database import get_db
from app.models import Alert, AgentMetric, ServerMetric


router = APIRouter(prefix="/config", tags=["config"])


class SystemConfig(BaseModel):
    collector_interval_min: int = Field(default=settings.COLLECTOR_INTERVAL_MIN, ge=1, le=3600)
    collector_interval_max: int = Field(default=settings.COLLECTOR_INTERVAL_MAX, ge=1, le=3600)
    data_retention_days: int = Field(default=settings.DATA_RETENTION_DAYS, ge=1, le=3650)
    resolved_alert_retention_days: int = Field(default=settings.RESOLVED_ALERT_RETENTION_DAYS, ge=1, le=3650)
    alert_cpu_threshold: float = Field(default=settings.ALERT_CPU_THRESHOLD, ge=0, le=100)
    alert_memory_threshold: float = Field(default=settings.ALERT_MEMORY_THRESHOLD, ge=0, le=100)
    alert_disk_threshold: float = Field(default=settings.ALERT_DISK_THRESHOLD, ge=0, le=100)


class RuntimeInfo(BaseModel):
    app_name: str
    app_version: str
    environment: str
    auth_required: bool
    ingest_token_configured: bool
    updated_at: datetime


_current_config = SystemConfig()


@router.get("", response_model=SystemConfig)
async def get_config(current_user: User = Depends(get_current_active_user)):
    return _current_config


@router.put("", response_model=SystemConfig)
async def update_config(config: SystemConfig, current_user: User = Depends(get_current_active_user)):
    global _current_config
    _current_config = config
    return _current_config


@router.get("/runtime", response_model=RuntimeInfo)
async def get_runtime_info():
    return RuntimeInfo(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        auth_required=settings.AUTH_REQUIRED,
        ingest_token_configured=bool(settings.INGEST_TOKEN),
        updated_at=datetime.now(timezone.utc),
    )


@router.get("/stats")
async def get_system_stats(db: AsyncSession = Depends(get_db)):
    server_count = await db.scalar(select(func.count(ServerMetric.id))) or 0
    agent_count = await db.scalar(select(func.count(AgentMetric.id))) or 0
    alert_count = await db.scalar(select(func.count(Alert.id))) or 0
    return {
        "total_metrics": server_count + agent_count,
        "server_metrics": server_count,
        "agent_metrics": agent_count,
        "total_alerts": alert_count,
        "version": settings.APP_VERSION,
    }
