"""Threat CRUD service"""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.models.models import Threat, ThreatSeverity, ThreatStatus
from app.schemas.threats import (
    ThreatListResponse, ThreatDetailResponse, ThreatUpdateRequest,
    ThreatStatsResponse, ThreatCreateRequest
)


class ThreatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_threat(self, tenant_id: UUID, payload: ThreatCreateRequest) -> Threat:
        threat = Threat(
            tenant_id=tenant_id,
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
            agent_id=payload.agent_id,
            mitre_tactic=payload.mitre_tactic,
            mitre_technique=payload.mitre_technique,
            source_ip=payload.source_ip,
            dest_ip=payload.dest_ip,
            process_name=payload.process_name,
            confidence_score=payload.confidence_score,
            anomaly_score=payload.anomaly_score,
            evidence=payload.evidence or {},
        )
        self.db.add(threat)
        await self.db.flush()
        await self.db.refresh(threat)
        return threat

    async def list_threats(self, tenant_id: UUID, page: int = 1, page_size: int = 50,
                           severity: Optional[ThreatSeverity] = None,
                           status: Optional[ThreatStatus] = None, **kwargs) -> ThreatListResponse:
        q = select(Threat).where(Threat.tenant_id == tenant_id)
        if severity:
            q = q.where(Threat.severity == severity)
        if status:
            q = q.where(Threat.status == status)
        q = q.order_by(Threat.created_at.desc())
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        threats = result.scalars().all()
        return ThreatListResponse(threats=threats, total=total, page=page, page_size=page_size)

    async def get_threat_detail(self, threat_id: UUID, tenant_id: UUID) -> Optional[Threat]:
        result = await self.db.execute(
            select(Threat).where(and_(Threat.id == threat_id, Threat.tenant_id == tenant_id))
        )
        return result.scalar_one_or_none()

    async def update_threat(self, threat_id: UUID, tenant_id: UUID,
                            payload: ThreatUpdateRequest, actor: str) -> Threat:
        threat = await self.get_threat_detail(threat_id, tenant_id)
        if not threat:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Threat not found")
        if payload.status:
            threat.status = payload.status
            if payload.status in (ThreatStatus.REMEDIATED, ThreatStatus.CLOSED):
                threat.resolved_at = datetime.utcnow()
        if payload.analyst_notes is not None:
            threat.analyst_notes = payload.analyst_notes
        if payload.severity:
            threat.severity = payload.severity
        await self.db.flush()
        await self.db.refresh(threat)
        return threat

    async def get_stats(self, tenant_id: UUID, window_hours: int = 24) -> ThreatStatsResponse:
        since = datetime.utcnow() - timedelta(hours=window_hours)
        result = await self.db.execute(select(Threat).where(Threat.tenant_id == tenant_id))
        all_threats = result.scalars().all()
        recent = [t for t in all_threats if t.created_at.replace(tzinfo=None) >= since]

        def count_sev(sev): return len([t for t in all_threats if t.severity == sev])
        active = len([t for t in all_threats if t.status in (ThreatStatus.DETECTED, ThreatStatus.INVESTIGATING)])
        remediated = len([t for t in all_threats if t.status == ThreatStatus.REMEDIATED])

        mitre = {}
        for t in all_threats:
            if t.mitre_tactic:
                mitre[t.mitre_tactic] = mitre.get(t.mitre_tactic, 0) + 1

        # Build simple trend (hourly for last 24h)
        trend = []
        for h in range(min(window_hours, 24)):
            bucket_start = datetime.utcnow() - timedelta(hours=h + 1)
            bucket_end = datetime.utcnow() - timedelta(hours=h)
            count = len([t for t in all_threats if bucket_start <= t.created_at.replace(tzinfo=None) < bucket_end])
            trend.append({"hour": h, "count": count})

        return ThreatStatsResponse(
            total=len(all_threats),
            critical=count_sev(ThreatSeverity.CRITICAL),
            high=count_sev(ThreatSeverity.HIGH),
            medium=count_sev(ThreatSeverity.MEDIUM),
            low=count_sev(ThreatSeverity.LOW),
            active=active,
            remediated=remediated,
            trend=trend,
            mitre_breakdown=mitre,
        )

    async def get_timeline(self, threat_id: UUID, tenant_id: UUID) -> list:
        return []  # Simplified — no timeline table in demo

    async def record_timeline_event(self, threat_id: UUID, event_type: str,
                                    actor: str, description: str, metadata: dict):
        pass  # Simplified for demo
