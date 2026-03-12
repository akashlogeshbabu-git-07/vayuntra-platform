"""Threat Pydantic schemas"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel
from app.db.models.models import ThreatSeverity, ThreatStatus


class ThreatResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    agent_id: Optional[UUID]
    title: str
    description: Optional[str]
    severity: ThreatSeverity
    status: ThreatStatus
    confidence_score: float
    anomaly_score: float
    mitre_tactic: Optional[str]
    mitre_technique: Optional[str]
    source_ip: Optional[str]
    dest_ip: Optional[str]
    process_name: Optional[str]
    evidence: Optional[Dict]
    remediation_playbook: Optional[str]
    analyst_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThreatListResponse(BaseModel):
    threats: List[ThreatResponse]
    total: int
    page: int
    page_size: int


class ThreatDetailResponse(ThreatResponse):
    pass


class ThreatUpdateRequest(BaseModel):
    status: Optional[ThreatStatus] = None
    analyst_notes: Optional[str] = None
    severity: Optional[ThreatSeverity] = None


class ThreatIsolateRequest(BaseModel):
    isolation_type: str = "network"
    reason: Optional[str] = None


class ThreatTimelineResponse(BaseModel):
    id: UUID
    threat_id: UUID
    event_type: str
    description: str
    actor: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ThreatStatsResponse(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int
    active: int
    remediated: int
    trend: List[Dict]
    mitre_breakdown: Dict[str, int]


class ThreatCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    severity: ThreatSeverity
    agent_id: Optional[UUID] = None
    mitre_tactic: Optional[str] = None
    mitre_technique: Optional[str] = None
    source_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    process_name: Optional[str] = None
    confidence_score: float = 0.8
    anomaly_score: float = 0.8
    evidence: Optional[Dict] = None
