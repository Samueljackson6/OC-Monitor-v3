"""Retention cleanup task for OC-Monitor data stores."""
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys
from sqlalchemy import delete

sys.path.insert(0, str(Path(__file__).parent / "api"))

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Alert, AgentMetric, ServerMetric


async def cleanup_old_data() -> dict[str, int]:
    metric_cutoff = time.time() - settings.DATA_RETENTION_DAYS * 24 * 60 * 60
    alert_cutoff = datetime.now() - timedelta(days=settings.RESOLVED_ALERT_RETENTION_DAYS)
    async with AsyncSessionLocal() as session:
        server_result = await session.execute(delete(ServerMetric).where(ServerMetric.timestamp < metric_cutoff))
        agent_result = await session.execute(delete(AgentMetric).where(AgentMetric.timestamp < metric_cutoff))
        alert_result = await session.execute(
            delete(Alert)
            .where(Alert.is_resolved.is_(True))
            .where(Alert.created_at < alert_cutoff)
        )
        await session.commit()
    return {
        "server_metrics_deleted": server_result.rowcount or 0,
        "agent_metrics_deleted": agent_result.rowcount or 0,
        "resolved_alerts_deleted": alert_result.rowcount or 0,
    }


def main() -> None:
    result = asyncio.run(cleanup_old_data())
    total = sum(result.values())
    print({**result, "total_deleted": total})


if __name__ == "__main__":
    main()
