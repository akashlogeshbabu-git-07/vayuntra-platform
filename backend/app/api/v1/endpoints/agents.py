"""Agents management endpoints"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_tenant
from app.db.models.models import Agent, AgentStatus, AgentOS

router = APIRouter()


class AgentCreate(BaseModel):
    hostname: str
    ip_address: str
    os: AgentOS
    os_version: Optional[str] = None
    tags: Optional[dict] = None


class AgentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    hostname: str
    ip_address: str
    os: AgentOS
    os_version: Optional[str]
    agent_version: str
    status: AgentStatus
    last_seen: Optional[datetime]
    tags: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/")
async def list_agents(
    status: Optional[AgentStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    q = select(Agent).where(Agent.tenant_id == tenant.id)
    if status:
        q = q.where(Agent.status == status)
    q = q.order_by(Agent.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    agents = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"agents": [AgentResponse.model_validate(a) for a in agents], "total": total, "page": page}


@router.post("/", status_code=201)
async def create_agent(
    payload: AgentCreate,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    agent = Agent(tenant_id=tenant.id, **payload.model_dump())
    db.add(agent)
    await db.flush()
    await db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}")
async def get_agent(
    agent_id: UUID,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant.id))
    agent = r.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}/status")
async def update_agent_status(
    agent_id: UUID,
    status: AgentStatus,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    r = await db.execute(select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant.id))
    agent = r.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.status = status
    agent.last_seen = datetime.utcnow()
    await db.flush()
    return AgentResponse.model_validate(agent)
