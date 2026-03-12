"""Behavioral Memory endpoint — persistent anomaly baseline per agent"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from datetime import datetime, timedelta
import random

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_tenant
from app.db.models.models import Threat, Agent

router = APIRouter()


class BehaviorProfile(BaseModel):
    agent_id: str
    hostname: str
    baseline_established: bool
    anomaly_rate_7d: float
    top_tactics: List[str]
    risk_score: float
    last_updated: str


class BehaviorSummary(BaseModel):
    profiles: List[BehaviorProfile]
    total_agents_profiled: int
    high_risk_agents: int


@router.get("/", response_model=BehaviorSummary)
async def list_behavioral_profiles(
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Return behavioral risk profiles per agent derived from threat history."""
    agents_result = await db.execute(select(Agent).where(Agent.tenant_id == tenant.id))
    agents = agents_result.scalars().all()

    threats_result = await db.execute(select(Threat).where(Threat.tenant_id == tenant.id))
    threats = threats_result.scalars().all()

    profiles = []
    for agent in agents:
        agent_threats = [t for t in threats if t.agent_id == agent.id]
        tactics = list({t.mitre_tactic for t in agent_threats if t.mitre_tactic})
        anomaly_rate = round(len(agent_threats) / 7, 2)
        risk = min(1.0, round(anomaly_rate / 5, 2)) if agent_threats else 0.0
        profiles.append(BehaviorProfile(
            agent_id=str(agent.id),
            hostname=agent.hostname,
            baseline_established=len(agent_threats) >= 3,
            anomaly_rate_7d=anomaly_rate,
            top_tactics=tactics[:3],
            risk_score=risk,
            last_updated=datetime.utcnow().isoformat(),
        ))

    high_risk = sum(1 for p in profiles if p.risk_score > 0.5)
    return BehaviorSummary(
        profiles=profiles,
        total_agents_profiled=len(profiles),
        high_risk_agents=high_risk,
    )


@router.get("/agent/{agent_id}")
async def get_agent_behavior(
    agent_id: UUID,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Return detailed behavioral timeline for a specific agent."""
    agent_result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant.id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent not found")

    threats_result = await db.execute(
        select(Threat).where(Threat.agent_id == agent_id, Threat.tenant_id == tenant.id)
    )
    threats = threats_result.scalars().all()

    timeline = [
        {
            "timestamp": t.created_at.isoformat(),
            "threat_id": str(t.id),
            "title": t.title,
            "severity": t.severity.value,
            "mitre_tactic": t.mitre_tactic,
            "anomaly_score": t.anomaly_score,
        }
        for t in sorted(threats, key=lambda x: x.created_at, reverse=True)
    ]

    return {
        "agent_id": str(agent_id),
        "hostname": agent.hostname,
        "total_threats": len(threats),
        "timeline": timeline,
    }
