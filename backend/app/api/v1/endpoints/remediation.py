"""Remediation management endpoints"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_tenant
from app.db.models.models import Threat, ThreatStatus
from app.services.ml.remediation_service import RemediationService

router = APIRouter()


class RemediationHistoryItem(BaseModel):
    threat_id: str
    title: str
    mitre_tactic: Optional[str]
    remediated_at: Optional[str]
    playbook_preview: Optional[str]


@router.get("/")
async def list_remediations(
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List all remediated threats with playbook metadata."""
    result = await db.execute(
        select(Threat).where(
            Threat.tenant_id == tenant.id,
            Threat.status == ThreatStatus.REMEDIATED,
        ).order_by(Threat.updated_at.desc())
    )
    threats = result.scalars().all()

    return {
        "remediations": [
            {
                "threat_id": str(t.id),
                "title": t.title,
                "severity": t.severity.value,
                "mitre_tactic": t.mitre_tactic,
                "mitre_technique": t.mitre_technique,
                "remediated_at": t.resolved_at.isoformat() if t.resolved_at else t.updated_at.isoformat(),
                "playbook_preview": (t.remediation_playbook or "")[:200],
                "has_full_playbook": bool(t.remediation_playbook),
            }
            for t in threats
        ],
        "total": len(threats),
    }


@router.post("/{threat_id}/run")
async def run_remediation(
    threat_id: UUID,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Trigger remediation for a threat (rule-based or LLM)."""
    svc = RemediationService(db)
    return await svc.trigger_remediation(
        threat_id=threat_id,
        tenant_id=tenant.id,
        actor=str(current_user.id),
        background_tasks=background_tasks,
    )


@router.get("/{threat_id}/playbook")
async def get_playbook(
    threat_id: UUID,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the remediation playbook for a specific threat."""
    result = await db.execute(
        select(Threat).where(Threat.id == threat_id, Threat.tenant_id == tenant.id)
    )
    threat = result.scalar_one_or_none()
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")

    if not threat.remediation_playbook:
        raise HTTPException(status_code=404, detail="No playbook generated yet. Run remediation first.")

    steps = [s.strip() for s in threat.remediation_playbook.strip().split("\n") if s.strip()]
    return {
        "threat_id": str(threat_id),
        "title": threat.title,
        "mitre_tactic": threat.mitre_tactic,
        "playbook": threat.remediation_playbook,
        "steps": steps,
        "status": threat.status.value,
    }
