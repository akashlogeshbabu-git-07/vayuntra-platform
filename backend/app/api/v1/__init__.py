"""Vayuntra — API v1 Router"""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, agents, threats, dashboard, telemetry, remediation, behavioral, tenants, users, llm, health

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(agents.router, prefix="/agents", tags=["Agents"])
router.include_router(threats.router, prefix="/threats", tags=["Threats"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(telemetry.router, prefix="/telemetry", tags=["Telemetry"])
router.include_router(remediation.router, prefix="/remediation", tags=["Remediation"])
router.include_router(behavioral.router, prefix="/behavioral", tags=["Behavioral"])
router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(llm.router, prefix="/llm", tags=["LLM"])
router.include_router(health.router, prefix="/health", tags=["Health"])
