"""
OC-Monitor v3.0 - 告警管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Alert


router = APIRouter(prefix="/alerts", tags=["alerts"])


# ========== Pydantic 模型 ==========

class AlertIn(BaseModel):
    """告警输入"""
    alert_type: str  # cpu, memory, disk, gateway
    severity: str    # critical, warning, info
    title: str
    message: Optional[str] = None


class AlertOut(BaseModel):
    """告警输出"""
    id: int
    alert_type: str
    severity: str
    title: str
    message: Optional[str]
    is_resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime


# ========== API 端点 ==========

@router.post("", response_model=AlertOut)
async def create_alert(
    alert: AlertIn,
    db: AsyncSession = Depends(get_db)
):
    """
    创建告警
    
    由系统自动触发或手动创建
    """
    try:
        new_alert = Alert(
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            message=alert.message
        )
        db.add(new_alert)
        await db.commit()
        await db.refresh(new_alert)
        
        return AlertOut(
            id=new_alert.id,
            alert_type=new_alert.alert_type,
            severity=new_alert.severity,
            title=new_alert.title,
            message=new_alert.message,
            is_resolved=new_alert.is_resolved,
            resolved_at=new_alert.resolved_at,
            created_at=new_alert.created_at
        )
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[AlertOut])
async def list_alerts(
    is_resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    获取告警列表
    
    支持按状态和严重程度筛选
    """
    query = select(Alert)
    
    if is_resolved is not None:
        query = query.where(Alert.is_resolved == is_resolved)
    
    if severity:
        query = query.where(Alert.severity == severity)
    
    query = query.order_by(Alert.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return [
        AlertOut(
            id=a.id,
            alert_type=a.alert_type,
            severity=a.severity,
            title=a.title,
            message=a.message,
            is_resolved=a.is_resolved,
            resolved_at=a.resolved_at,
            created_at=a.created_at
        )
        for a in alerts
    ]


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    解决告警
    
    标记告警为已解决
    """
    try:
        result = await db.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .values(is_resolved=True, resolved_at=datetime.now())
        )
        await db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="告警不存在")
        
        return {"status": "ok", "alert_id": alert_id}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def alert_stats(db: AsyncSession = Depends(get_db)):
    """
    获取告警统计
    
    返回各级别告警数量
    """
    # 未解决告警统计
    result = await db.execute(
        select(Alert.severity, func.count(Alert.id))
        .where(Alert.is_resolved == False)
        .group_by(Alert.severity)
    )
    
    unresolved = {row[0]: row[1] for row in result.all()}
    
    # 今日告警数
    from datetime import timedelta
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(Alert.id))
        .where(Alert.created_at >= today_start)
    )
    today_count = result.scalar()
    
    return {
        "unresolved": {
            "critical": unresolved.get("critical", 0),
            "warning": unresolved.get("warning", 0),
            "info": unresolved.get("info", 0)
        },
        "today_count": today_count
    }


# 需要导入 func
from sqlalchemy import func
