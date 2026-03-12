"""Dashboard stats endpoint"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user, get_current_tenant
from app.db.models.models import Threat, Agent, User, ThreatStatus, AgentStatus
from sqlalchemy import select, func

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    window_hours: int = Query(24, ge=1, le=720),
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    from app.services.threat.threat_service import ThreatService
    svc = ThreatService(db)
    stats = await svc.get_stats(tenant.id, window_hours)

    # Agent counts
    r = await db.execute(select(func.count()).where(Agent.tenant_id == tenant.id))
    total_agents = r.scalar() or 0
    r = await db.execute(select(func.count()).where(Agent.tenant_id == tenant.id, Agent.status == AgentStatus.ONLINE))
    online_agents = r.scalar() or 0

    return {
        **stats.model_dump(),
        "total_agents": total_agents,
        "online_agents": online_agents,
    }
