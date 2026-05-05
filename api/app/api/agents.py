"""
OC-Monitor v3.0 - Agent 管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AgentMetric


router = APIRouter(prefix="/agents", tags=["agents"])


# ========== Pydantic 模型 ==========

class AgentMetricIn(BaseModel):
    """Agent 指标输入"""
    agent_id: str
    agent_name: Optional[str] = None
    status: str  # online, offline
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    timestamp: float


class AgentMetricOut(BaseModel):
    """Agent 指标输出"""
    agent_id: str
    agent_name: Optional[str]
    status: str
    memory_mb: Optional[float]
    cpu_percent: Optional[float]
    timestamp: float
    collected_at: Optional[datetime] = None


class AgentSummary(BaseModel):
    """Agent 汇总"""
    agent_id: str
    agent_name: Optional[str]
    status: str
    latest_memory: Optional[float]
    latest_cpu: Optional[float]
    last_seen: Optional[datetime]


# ========== API 端点 ==========

@router.post("/metrics")
async def receive_agent_metric(
    metric: AgentMetricIn,
    db: AsyncSession = Depends(get_db)
):
    """
    接收 Agent 指标
    
    由 Agent 采集端调用，上报 Agent 状态
    """
    try:
        agent_metric = AgentMetric(
            agent_id=metric.agent_id,
            agent_name=metric.agent_name,
            status=metric.status,
            memory_mb=metric.memory_mb,
            cpu_percent=metric.cpu_percent,
            timestamp=metric.timestamp
        )
        db.add(agent_metric)
        await db.commit()
        
        return {"status": "ok", "agent_id": metric.agent_id}
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=List[AgentSummary])
async def list_agents(db: AsyncSession = Depends(get_db)):
    """
    获取所有 Agent 列表
    
    返回每个 Agent 的最新状态
    """
    # 子查询：每个 agent 的最新记录
    subquery = (
        select(
            AgentMetric.agent_id,
            func.max(AgentMetric.timestamp).label('max_timestamp')
        )
        .group_by(AgentMetric.agent_id)
        .subquery()
    )
    
    # 关联查询获取完整信息
    result = await db.execute(
        select(AgentMetric)
        .join(
            subquery,
            (AgentMetric.agent_id == subquery.c.agent_id) &
            (AgentMetric.timestamp == subquery.c.max_timestamp)
        )
    )
    
    agents = result.scalars().all()
    
    return [
        AgentSummary(
            agent_id=agent.agent_id,
            agent_name=agent.agent_name,
            status=agent.status,
            latest_memory=agent.memory_mb,
            latest_cpu=agent.cpu_percent,
            last_seen=agent.collected_at
        )
        for agent in agents
    ]


@router.get("/{agent_id}/history", response_model=List[AgentMetricOut])
async def get_agent_history(
    agent_id: str,
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定 Agent 的历史数据
    """
    # 计算时间范围
    now = datetime.now()
    from datetime import timedelta
    start_time = now - timedelta(hours=hours)
    start_timestamp = start_time.timestamp()
    
    result = await db.execute(
        select(AgentMetric)
        .where(AgentMetric.agent_id == agent_id)
        .where(AgentMetric.timestamp >= start_timestamp)
        .order_by(AgentMetric.timestamp.desc())
        .limit(1000)
    )
    
    metrics = result.scalars().all()
    
    return [
        AgentMetricOut(
            agent_id=m.agent_id,
            agent_name=m.agent_name,
            status=m.status,
            memory_mb=m.memory_mb,
            cpu_percent=m.cpu_percent,
            timestamp=m.timestamp,
            collected_at=m.collected_at
        )
        for m in metrics
    ]
