import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import audit
from app.db import get_db
from app.deps import require_role
from app.models import Role, User
from app.schemas import UserCreateIn, UserOut, UserUpdateIn
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(_: User = Depends(require_role(Role.manager)), db: Session = Depends(get_db)) -> list[User]:
    """Users in your organization (managers and admins)."""
    return list(db.execute(select(User).order_by(User.created_at)).scalars())


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreateIn,
    admin: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
) -> User:
    """Add a user to your organization (admins only)."""
    email = body.email.lower()
    taken = db.execute(
        select(User.id).where(User.email == email).execution_options(skip_tenant_filter=True)
    ).first()
    if taken is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        id=uuid.uuid4(),
        org_id=admin.org_id,
        email=email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    audit.record(db, admin, "user.created", "user", user.id, {"role": body.role.value})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists") from None
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    body: UserUpdateIn,
    admin: User = Depends(require_role(Role.admin)),
    db: Session = Depends(get_db),
) -> User:
    """Change a user's role or deactivate/reactivate them (admins only)."""
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if user is None:  # also what you get for a user in another organization
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "You cannot change your own role or status; ask another admin",
        )

    changes: dict[str, str | bool] = {}
    if body.role is not None and body.role != user.role:
        user.role = body.role
        changes["role"] = body.role.value
    if body.is_active is not None and body.is_active != user.is_active:
        user.is_active = body.is_active
        changes["is_active"] = body.is_active

    if changes:
        audit.record(db, admin, "user.updated", "user", user.id, changes)
        db.commit()
    return user
