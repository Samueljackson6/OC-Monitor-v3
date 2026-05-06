"""Server metrics API."""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import ServerMetric
from app.security import require_ingest_token


router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricIn(BaseModel):
    cpu: float = Field(ge=0, le=100)
    memory: float = Field(ge=0, le=100)
    disk: float = Field(ge=0, le=100)
    gateway_status: bool
    timestamp: float


class BatchMetricsIn(BaseModel):
    metrics: List[MetricIn]


class MetricOut(BaseModel):
    cpu: float
    memory: float
    disk: float
    gateway_status: bool
    timestamp: float
    collected_at: Optional[datetime] = None


class HistoryOut(BaseModel):
    time: str
    cpu: float
    memory: float
    disk: float


@router.post("/batch")
async def receive_metrics(
    batch: BatchMetricsIn,
    db: AsyncSession = Depends(get_db),
    _token: None = Depends(require_ingest_token),
):
    if not batch.metrics:
        return {"received": 0}
    try:
        for m in batch.metrics:
            db.add(ServerMetric(
                cpu=m.cpu,
                memory=m.memory,
                disk=m.disk,
                gateway_status=m.gateway_status,
                timestamp=m.timestamp,
            ))
        await db.commit()
        return {"received": len(batch.metrics)}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to store metrics") from exc


@router.get("/realtime", response_model=MetricOut)
async def get_realtime(db: AsyncSession = Depends(get_db)):
    metric = await db.scalar(select(ServerMetric).order_by(ServerMetric.timestamp.desc()).limit(1))
    if metric is None:
        raise HTTPException(status_code=404, detail="No data available")
    return MetricOut(
        cpu=metric.cpu,
        memory=metric.memory,
        disk=metric.disk,
        gateway_status=metric.gateway_status,
        timestamp=metric.timestamp,
        collected_at=metric.collected_at,
    )


@router.get("/history", response_model=List[HistoryOut])
async def get_history(hours: int = 24, db: AsyncSession = Depends(get_db)):
    hours = max(1, min(hours, 24 * 30))
    start_timestamp = (datetime.now() - timedelta(hours=hours)).timestamp()
    result = await db.execute(
        select(ServerMetric)
        .where(ServerMetric.timestamp >= start_timestamp)
        .order_by(ServerMetric.timestamp.asc())
        .limit(10000)
    )
    groups = defaultdict(list)
    for metric in result.scalars().all():
        collected_at = metric.collected_at or datetime.fromtimestamp(metric.timestamp)
        key = collected_at.strftime("%Y-%m-%d %H:%M")
        groups[key].append(metric)
    return [
        HistoryOut(
            time=key,
            cpu=round(sum(m.cpu for m in values) / len(values), 2),
            memory=round(sum(m.memory for m in values) / len(values), 2),
            disk=round(sum(m.disk for m in values) / len(values), 2),
        )
        for key, values in sorted(groups.items())
    ]


@router.get("/health")
async def health_check():
    return {"status": "ok"}
