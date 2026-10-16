from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record(
    db: Session,
    user: User,
    action: str,
    resource_type: str | None = None,
    resource_id: object | None = None,
    detail: dict | None = None,
) -> None:
    """Add an audit entry to the current transaction (the caller commits).

    Never put patient data in `detail`: it is meant for ids and field names only.
    """
    db.add(
        AuditLog(
            org_id=user.org_id,
            user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            detail=detail,
        )
    )
