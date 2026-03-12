"""Isolation service — dispatches isolation commands to agents"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.models import Threat, ThreatStatus, AgentStatus, Agent
from sqlalchemy import select

log = structlog.get_logger(__name__)


class IsolationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def isolate(self, threat: Threat, isolation_type: str, actor: str) -> Threat:
        log.info("isolation.triggered", threat_id=str(threat.id), type=isolation_type, actor=actor)
        # Update threat status
        threat.status = ThreatStatus.CONTAINED
        # If agent exists, mark as isolated
        if threat.agent_id:
            result = await self.db.execute(select(Agent).where(Agent.id == threat.agent_id))
            agent = result.scalar_one_or_none()
            if agent:
                agent.status = AgentStatus.ISOLATED
        await self.db.flush()
        await self.db.refresh(threat)
        return threat
