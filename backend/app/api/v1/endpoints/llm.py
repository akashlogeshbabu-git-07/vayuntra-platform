"""LLM remediation endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_tenant
from app.schemas.llm import RemediationRequest, RemediationResponse, RootCauseAnalysis
from app.services.llm.llm_engine import get_llm_engine
from app.db.models.models import Threat

router = APIRouter()


@router.get("/status")
async def llm_status(current_user=Depends(get_current_user)):
    """Return LLM engine availability status."""
    from app.core.config import settings
    import os
    model_present = os.path.exists(settings.LLM_MODEL_PATH)
    return {
        "llm_enabled": settings.LLM_ENABLED,
        "model_path": settings.LLM_MODEL_PATH,
        "model_present": model_present,
        "cloud_fallback": settings.LLM_CLOUD_FALLBACK,
        "engine": "local_mistral_7b" if (settings.LLM_ENABLED and model_present) else "rule_based",
    }


@router.post("/remediate", response_model=RemediationResponse)
async def generate_remediation(
    payload: RemediationRequest,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI remediation playbook for a threat."""
    engine = get_llm_engine()
    return await engine.generate_remediation(
        request=payload,
        user_id=str(current_user.id),
        tenant_id=str(tenant.id),
    )


@router.post("/root-cause/{threat_id}", response_model=RootCauseAnalysis)
async def root_cause_analysis(
    threat_id: UUID,
    current_user=Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Generate root cause analysis for a specific threat."""
    result = await db.execute(
        select(Threat).where(Threat.id == threat_id, Threat.tenant_id == tenant.id)
    )
    threat = result.scalar_one_or_none()
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")

    threat_data = {
        "id": str(threat.id),
        "title": threat.title,
        "severity": threat.severity.value,
        "status": threat.status.value,
        "mitre_tactic": threat.mitre_tactic,
        "mitre_technique": threat.mitre_technique,
        "source_ip": threat.source_ip,
        "dest_ip": threat.dest_ip,
        "process_name": threat.process_name,
        "anomaly_score": threat.anomaly_score,
        "confidence_score": threat.confidence_score,
        "evidence": threat.evidence,
    }

    engine = get_llm_engine()
    return await engine.generate_root_cause(
        threat_data=threat_data,
        user_id=str(current_user.id),
        tenant_id=str(tenant.id),
    )
