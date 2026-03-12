"""Tenant management endpoints (super_admin only)"""
from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user, require_roles
from app.db.models.models import Tenant, User, Agent, Threat, UserRole

router = APIRouter()


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    max_agents: int
    created_at: datetime

    class Config:
        from_attributes = True


class TenantCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    max_agents: int = 100


@router.get("/")
async def list_tenants(
    current_user=Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.TENANT_ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    out = []
    for t in tenants:
        user_count = (await db.execute(
            select(func.count()).where(User.tenant_id == t.id)
        )).scalar() or 0
        agent_count = (await db.execute(
            select(func.count()).where(Agent.tenant_id == t.id)
        )).scalar() or 0
        out.append({
            **TenantResponse.model_validate(t).model_dump(),
            "user_count": user_count,
            "agent_count": agent_count,
        })
    return {"tenants": out, "total": len(out)}


@router.post("/", status_code=201)
async def create_tenant(
    payload: TenantCreate,
    current_user=Depends(require_roles([UserRole.SUPER_ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    slug = payload.slug or payload.name.lower().replace(" ", "-")
    tenant = Tenant(name=payload.name, slug=slug, max_agents=payload.max_agents)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.get("/me")
async def get_my_tenant(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)
