"""Health check endpoints"""
from fastapi import APIRouter
from app.core.health import check_all_dependencies

router = APIRouter()


@router.get("/")
async def health():
    """Full dependency health check."""
    result = await check_all_dependencies()
    status_code = 200 if result.get("ready") else 503
    return result


@router.get("/ping")
async def ping():
    """Lightweight liveness probe."""
    return {"status": "ok"}
