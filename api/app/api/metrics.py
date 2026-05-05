"""
OC-Monitor v3.0 - 指标 API
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ServerMetric, AgentMetric


router = APIRouter(prefix="/metrics", tags=["metrics"])


# ========== Pydantic 模型 ==========

class MetricIn(BaseModel):
    """指标输入"""
    cpu: float
    memory: float
    disk: float
    gateway_status: bool
    timestamp: float


class BatchMetricsIn(BaseModel):
    """批量指标输入"""
    metrics: List[MetricIn]


class MetricOut(BaseModel):
    """指标输出"""
    cpu: float
    memory: float
    disk: float
    gateway_status: bool
    timestamp: float
    collected_at: Optional[datetime] = None


class HistoryOut(BaseModel):
    """历史数据输出"""
    time: str
    cpu: float
    memory: float
    disk: float


# ========== API 端点 ==========

@router.post("/batch")
async def receive_metrics(
    batch: BatchMetricsIn,
    db: AsyncSession = Depends(get_db)
):
    """
    接收批量指标
    
    由采集端调用，批量推送监控数据
    """
    try:
        # 批量插入
        for m in batch.metrics:
            metric = ServerMetric(
                cpu=m.cpu,
                memory=m.memory,
                disk=m.disk,
                gateway_status=m.gateway_status,
                timestamp=m.timestamp
            )
            db.add(metric)
        
        await db.commit()
        
        return {"received": len(batch.metrics)}
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime", response_model=MetricOut)
async def get_realtime(db: AsyncSession = Depends(get_db)):
    """
    获取实时数据
    
    返回最新的一条监控数据
    """
    result = await db.execute(
        select(ServerMetric)
        .order_by(ServerMetric.timestamp.desc())
        .limit(1)
    )
    metric = result.scalar_one_or_none()
    
    if not metric:
        raise HTTPException(status_code=404, detail="No data available")
    
    return MetricOut(
        cpu=metric.cpu,
        memory=metric.memory,
        disk=metric.disk,
        gateway_status=metric.gateway_status,
        timestamp=metric.timestamp,
        collected_at=metric.collected_at
    )


@router.get("/history", response_model=List[HistoryOut])
async def get_history(
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """
    获取历史趋势
    
    返回指定时间范围内的聚合数据
    """
    # 计算时间范围
    now = datetime.now()
    start_time = now - timedelta(hours=hours)
    start_timestamp = start_time.timestamp()
    
    # 查询并按分钟聚合
    result = await db.execute(
        select(
            func.strftime('%Y-%m-%d %H:%M', ServerMetric.collected_at).label('time'),
            func.avg(ServerMetric.cpu).label('cpu'),
            func.avg(ServerMetric.memory).label('memory'),
            func.avg(ServerMetric.disk).label('disk')
        )
        .where(ServerMetric.timestamp >= start_timestamp)
        .group_by('time')
        .order_by('time')
    )
    
    rows = result.all()
    
    return [
        HistoryOut(
            time=row.time,
            cpu=round(row.cpu, 2),
            memory=round(row.memory, 2),
            disk=round(row.disk, 2)
        )
        for row in rows
    ]


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}
