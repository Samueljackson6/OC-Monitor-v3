"""Agent metrics API."""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import AgentMetric
from app.security import require_ingest_token


router = APIRouter(prefix="/agents", tags=["agents"])


class AgentMetricIn(BaseModel):
    agent_id: str
    agent_name: Optional[str] = None
    status: str
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    timestamp: float


class AgentMetricOut(BaseModel):
    agent_id: str
    agent_name: Optional[str]
    status: str
    memory_mb: Optional[float]
    cpu_percent: Optional[float]
    timestamp: float
    collected_at: Optional[datetime] = None


class AgentSummary(BaseModel):
    agent_id: str
    agent_name: Optional[str]
    status: str
    latest_memory: Optional[float]
    latest_cpu: Optional[float]
    last_seen: Optional[datetime]


@router.post("/metrics")
async def receive_agent_metric(
    metric: AgentMetricIn,
    db: AsyncSession = Depends(get_db),
    _token: None = Depends(require_ingest_token),
):
    try:
        db.add(AgentMetric(
            agent_id=metric.agent_id,
            agent_name=metric.agent_name,
            status=metric.status,
            memory_mb=metric.memory_mb,
            cpu_percent=metric.cpu_percent,
            timestamp=metric.timestamp,
        ))
        await db.commit()
        return {"status": "ok", "agent_id": metric.agent_id}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to store agent metric") from exc


@router.get("/list", response_model=List[AgentSummary])
async def list_agents(db: AsyncSession = Depends(get_db)):
    subquery = (
        select(AgentMetric.agent_id, func.max(AgentMetric.timestamp).label("max_timestamp"))
        .group_by(AgentMetric.agent_id)
        .subquery()
    )
    result = await db.execute(
        select(AgentMetric)
        .join(
            subquery,
            (AgentMetric.agent_id == subquery.c.agent_id)
            & (AgentMetric.timestamp == subquery.c.max_timestamp),
        )
        .order_by(AgentMetric.agent_id.asc())
    )
    return [
        AgentSummary(
            agent_id=agent.agent_id,
            agent_name=agent.agent_name,
            status=agent.status,
            latest_memory=agent.memory_mb,
            latest_cpu=agent.cpu_percent,
            last_seen=agent.collected_at,
        )
        for agent in result.scalars().all()
    ]


@router.get("/{agent_id}/history", response_model=List[AgentMetricOut])
async def get_agent_history(agent_id: str, hours: int = 24, db: AsyncSession = Depends(get_db)):
    hours = max(1, min(hours, 24 * 30))
    start_timestamp = (datetime.now() - timedelta(hours=hours)).timestamp()
    result = await db.execute(
        select(AgentMetric)
        .where(AgentMetric.agent_id == agent_id)
        .where(AgentMetric.timestamp >= start_timestamp)
        .order_by(AgentMetric.timestamp.desc())
        .limit(1000)
    )
    return [
        AgentMetricOut(
            agent_id=m.agent_id,
            agent_name=m.agent_name,
            status=m.status,
            memory_mb=m.memory_mb,
            cpu_percent=m.cpu_percent,
            timestamp=m.timestamp,
            collected_at=m.collected_at,
        )
        for m in result.scalars().all()
    ]
