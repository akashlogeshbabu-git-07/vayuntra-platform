"""Health checks"""
from app.core.database import engine


async def check_all_dependencies() -> dict:
    checks = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"
    checks["ready"] = all("unhealthy" not in v for v in checks.values())
    return checks
