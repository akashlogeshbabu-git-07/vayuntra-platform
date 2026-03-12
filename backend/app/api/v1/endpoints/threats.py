"""Threats API Endpoint"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_tenant
from app.db.models.models import UserRole, ThreatSeverity, ThreatStatus
from app.schemas.threats import (
    ThreatResponse, ThreatListResponse, ThreatDetailResponse,
    ThreatUpdateRequest, ThreatIsolateRequest, ThreatStatsResponse, ThreatCreateRequest
)
from app.services.threat.threat_service import ThreatService
from app.services.threat.isolation_service import IsolationService
from app.services.ml.remediation_service import RemediationService

router = APIRouter()


@router.get("/", response_model=ThreatListResponse)
async def list_threats(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    severity: Optional[ThreatSeverity] = None,
    status: Optional[ThreatStatus] = None,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    svc = ThreatService(db)
    return await svc.list_threats(tenant_id=tenant.id, page=page, page_size=page_size,
                                   severity=severity, status=status)


@router.post("/", response_model=ThreatResponse, status_code=201)
async def create_threat(
    payload: ThreatCreateRequest,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    svc = ThreatService(db)
    return await svc.create_threat(tenant_id=tenant.id, payload=payload)


@router.get("/stats", response_model=ThreatStatsResponse)
async def get_threat_stats(
    window_hours: int = Query(24, ge=1, le=720),
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    svc = ThreatService(db)
    return await svc.get_stats(tenant_id=tenant.id, window_hours=window_hours)


@router.get("/{threat_id}", response_model=ThreatDetailResponse)
async def get_threat(
    threat_id: UUID,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    svc = ThreatService(db)
    threat = await svc.get_threat_detail(threat_id=threat_id, tenant_id=tenant.id)
    if not threat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threat not found")
    return threat


@router.patch("/{threat_id}", response_model=ThreatResponse)
async def update_threat(
    threat_id: UUID,
    payload: ThreatUpdateRequest,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    svc = ThreatService(db)
    return await svc.update_threat(threat_id=threat_id, tenant_id=tenant.id,
                                   payload=payload, actor=str(current_user.id))


@router.post("/{threat_id}/isolate", response_model=ThreatResponse)
async def isolate_threat(
    threat_id: UUID,
    payload: ThreatIsolateRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    svc = ThreatService(db)
    iso_svc = IsolationService(db)
    threat = await svc.get_threat_detail(threat_id=threat_id, tenant_id=tenant.id)
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")
    return await iso_svc.isolate(threat=threat, isolation_type=payload.isolation_type, actor=str(current_user.id))


@router.post("/{threat_id}/remediate")
async def trigger_remediation(
    threat_id: UUID,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    svc = RemediationService(db)
    return await svc.trigger_remediation(
        threat_id=threat_id, tenant_id=tenant.id,
        actor=str(current_user.id), background_tasks=background_tasks
    )
