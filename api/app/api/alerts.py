"""Alerts API."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import User, get_current_active_user
from app.database import get_db
from app.models import Alert
from app.security import require_ingest_token


router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertIn(BaseModel):
    alert_type: str
    severity: str
    title: str
    message: Optional[str] = None


class AlertOut(BaseModel):
    id: int
    alert_type: str
    severity: str
    title: str
    message: Optional[str]
    is_resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime


@router.post("", response_model=AlertOut)
async def create_alert(
    alert: AlertIn,
    db: AsyncSession = Depends(get_db),
    _token: None = Depends(require_ingest_token),
):
    try:
        new_alert = Alert(
            alert_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            message=alert.message,
        )
        db.add(new_alert)
        await db.commit()
        await db.refresh(new_alert)
        return new_alert
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create alert") from exc


@router.get("", response_model=List[AlertOut])
async def list_alerts(
    is_resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 500))
    query = select(Alert)
    if is_resolved is not None:
        query = query.where(Alert.is_resolved.is_(is_resolved))
    if severity:
        query = query.where(Alert.severity == severity)
    result = await db.execute(query.order_by(Alert.created_at.desc()).limit(limit))
    return list(result.scalars().all())


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        result = await db.execute(
            update(Alert)
            .where(Alert.id == alert_id)
            .values(is_resolved=True, resolved_at=datetime.now())
        )
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"status": "ok", "alert_id": alert_id}
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to resolve alert") from exc


@router.get("/stats")
async def alert_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Alert.severity, func.count(Alert.id))
        .where(Alert.is_resolved.is_(False))
        .group_by(Alert.severity)
    )
    unresolved = {row[0]: row[1] for row in result.all()}
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = await db.scalar(select(func.count(Alert.id)).where(Alert.created_at >= today_start)) or 0
    return {
        "unresolved": {
            "critical": unresolved.get("critical", 0),
            "warning": unresolved.get("warning", 0),
            "info": unresolved.get("info", 0),
        },
        "today_count": today_count,
    }
