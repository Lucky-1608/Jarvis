"""
Jarvis OS - Security Audit Logger

Provides functions to log sensitive actions to the relational database.
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from jarvis.database.models import AuditLog

logger = structlog.get_logger(__name__)

async def log_action(
    session: AsyncSession,
    action: str,
    user_id: int | None = None,
    details: dict | None = None
) -> None:
    """Logs an action to the audit log."""
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            details=details or {}
        )
        session.add(audit_entry)
        await session.commit()
        logger.info("audit.logged", action=action, user_id=user_id)
    except Exception as e:
        await session.rollback()
        logger.error("audit.failed", action=action, error=str(e))
