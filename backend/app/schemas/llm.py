"""LLM Pydantic schemas"""
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel


class LLMRequest(BaseModel):
    prompt: str
    max_tokens: int = 512
    temperature: float = 0.1


class LLMResponse(BaseModel):
    response: str
    model: str
    tokens_used: int
    inference_time_ms: float


class RemediationRequest(BaseModel):
    threat_id: str
    threat_type: Optional[str] = None
    threat_title: Optional[str] = None
    threat_description: Optional[str] = None
    mitre_technique: Optional[str] = None
    severity: str = "medium"
    evidence: Optional[dict] = None
    affected_processes: Optional[List[str]] = None
    anomaly_score: Optional[float] = None
    os_type: Optional[str] = None
    detection_model: Optional[str] = None
    analyst_question: Optional[str] = None


class RemediationResponse(BaseModel):
    threat_id: str
    playbook: Optional[str] = None
    content: Optional[str] = None
    steps: Optional[List[str]] = None
    model_used: Optional[str] = None
    engine: Optional[str] = None
    generated_at: Optional[str] = None
    inference_ms: Optional[int] = None
    is_safe: Optional[bool] = True
    error: Optional[str] = None


class RemediationPlaybook(BaseModel):
    threat_id: str
    title: str
    steps: List[str]
    mitre_technique: Optional[str] = None
    severity: Optional[str] = None


class RootCauseAnalysis(BaseModel):
    threat_id: Optional[str] = None
    analysis: str
    engine: Optional[str] = None
    kill_chain_stage: Optional[str] = None
