"""Audit logging — append-only structured event log"""
import structlog

log = structlog.get_logger(__name__)


async def log_event(event: str, user_id: str = None, tenant_id: str = None, **kwargs):
    """Log a named audit event."""
    log.info("audit_event", event=event, user_id=user_id, tenant_id=tenant_id, **kwargs)


async def audit_log(action: str, user_id: str = None, tenant_id: str = None, metadata: dict = None):
    """Structured audit entry — alias used by LLM engine."""
    log.info(
        "audit",
        action=action,
        user_id=user_id,
        tenant_id=tenant_id,
        **(metadata or {}),
    )
