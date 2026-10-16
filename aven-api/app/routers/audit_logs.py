from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_role
from app.models import AuditLog, Role, User
from app.schemas import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    """Newest first. Admins only."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars())
