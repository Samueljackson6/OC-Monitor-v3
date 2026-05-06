"""Request authentication dependencies."""
from secrets import compare_digest
from typing import Optional
from fastapi import Header, HTTPException, status
from app.config import settings


def require_ingest_token(x_oc_monitor_token: Optional[str] = Header(default=None)):
    if not settings.INGEST_TOKEN:
        return
    if not x_oc_monitor_token or not compare_digest(x_oc_monitor_token, settings.INGEST_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ingest token")
