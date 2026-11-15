from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog


def record_activity(
    db: Session,
    *,
    parent_id: int,
    email_parent: str,
    action: str,
    entity_type: str,
    entity_id: str | int,
    member_id: Optional[str] = None,
    details: Optional[str] = None,
) -> ActivityLog:
    """Registra automáticamente un evento en la bitácora de auditoría (`activity_logs`)."""
    log_entry = ActivityLog(
        created_at=datetime.now(timezone.utc),
        parent_id=parent_id,
        email_parent=email_parent,
        member_id=member_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
