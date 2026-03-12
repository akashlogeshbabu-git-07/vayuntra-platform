"""Telemetry ingest endpoint — agents push telemetry here"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_tenant
from app.db.models.models import Agent, AgentStatus, Threat, ThreatSeverity, ThreatStatus

router = APIRouter()


class TelemetryEvent(BaseModel):
    agent_id: UUID
    event_type: str           # process_start | network_conn | file_write | auth_event
    process_name: Optional[str] = None
    source_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    dest_port: Optional[int] = None
    user_account: Optional[str] = None
    file_path: Optional[str] = None
    command_line: Optional[str] = None
    anomaly_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class TelemetryBatch(BaseModel):
    events: List[TelemetryEvent]


@router.post("/ingest")
async def ingest_telemetry(
    payload: TelemetryBatch,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest a batch of telemetry events from an endpoint agent.
    High-anomaly events (score >= 0.85) automatically create threat records.
    """
    threats_created = 0
    agent_ids_seen: set = set()

    for event in payload.events:
        # Update agent last_seen
        if event.agent_id not in agent_ids_seen:
            result = await db.execute(
                select(Agent).where(Agent.id == event.agent_id, Agent.tenant_id == tenant.id)
            )
            agent = result.scalar_one_or_none()
            if agent:
                agent.last_seen = datetime.utcnow()
                agent_ids_seen.add(event.agent_id)

        # Auto-create threat if anomaly score is high
        if event.anomaly_score and event.anomaly_score >= 0.85:
            threat = Threat(
                tenant_id=tenant.id,
                agent_id=event.agent_id,
                title=f"Auto-detected: {event.event_type} — {event.process_name or event.source_ip or 'unknown'}",
                description=f"High anomaly score ({event.anomaly_score:.2f}) on {event.event_type} event.",
                severity=ThreatSeverity.HIGH if event.anomaly_score >= 0.92 else ThreatSeverity.MEDIUM,
                status=ThreatStatus.DETECTED,
                anomaly_score=event.anomaly_score,
                confidence_score=event.anomaly_score,
                source_ip=event.source_ip,
                dest_ip=event.dest_ip,
                process_name=event.process_name,
                evidence={
                    "event_type": event.event_type,
                    "command_line": event.command_line,
                    "dest_port": event.dest_port,
                    **(event.metadata or {}),
                },
            )
            db.add(threat)
            threats_created += 1

    await db.commit()
    return {
        "received": len(payload.events),
        "threats_auto_created": threats_created,
        "agents_updated": len(agent_ids_seen),
    }


@router.get("/summary")
async def telemetry_summary(
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """High-level telemetry ingestion summary per agent."""
    result = await db.execute(select(Agent).where(Agent.tenant_id == tenant.id))
    agents = result.scalars().all()

    return {
        "total_agents": len(agents),
        "online": sum(1 for a in agents if a.status == AgentStatus.ONLINE),
        "offline": sum(1 for a in agents if a.status == AgentStatus.OFFLINE),
        "isolated": sum(1 for a in agents if a.status == AgentStatus.ISOLATED),
        "agents": [
            {
                "id": str(a.id),
                "hostname": a.hostname,
                "status": a.status.value,
                "last_seen": a.last_seen.isoformat() if a.last_seen else None,
            }
            for a in agents
        ],
    }
