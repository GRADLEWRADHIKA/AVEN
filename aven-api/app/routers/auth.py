import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import audit
from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import Organization, Role, User
from app.schemas import LoginIn, MeOut, RegisterOrganizationIn, TokenOut
from app.security import burn_password_check, create_access_token, hash_password, verify_password

router = APIRouter(tags=["auth"])


def _find_user_by_email(db: Session, email: str) -> User | None:
    # Unscoped on purpose: emails are unique across the whole platform, and at login
    # we do not know the organization yet.
    return db.execute(
        select(User).where(User.email == email).execution_options(skip_tenant_filter=True)
    ).scalar_one_or_none()


@router.post("/auth/register-organization", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register_organization(body: RegisterOrganizationIn, db: Session = Depends(get_db)) -> TokenOut:
    """Create a new organization and its first admin user, and sign that admin in."""
    if not get_settings().allow_org_signup:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organization sign-up is disabled")

    email = body.email.lower()
    if _find_user_by_email(db, email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    org = Organization(id=uuid.uuid4(), name=body.organization_name)
    db.add(org)
    db.info["org_id"] = org.id
    admin = User(
        id=uuid.uuid4(),
        org_id=org.id,
        email=email,
        full_name=body.admin_name,
        password_hash=hash_password(body.password),
        role=Role.admin,
    )
    db.add(admin)
    audit.record(db, admin, "organization.registered", "organization", org.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists") from None

    token, expires_in = create_access_token(admin.id, admin.org_id, admin.role.value)
    return TokenOut(access_token=token, expires_in=expires_in)


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = _find_user_by_email(db, body.email.lower())
    if user is None:
        burn_password_check(body.password)  # keep timing the same as a real check
        valid = False
    else:
        valid = verify_password(body.password, user.password_hash) and user.is_active

    if not valid or user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db.info["org_id"] = user.org_id
    audit.record(db, user, "auth.login", "user", user.id)
    db.commit()

    token, expires_in = create_access_token(user.id, user.org_id, user.role.value)
    return TokenOut(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeOut:
    org = db.execute(select(Organization).where(Organization.id == user.org_id)).scalar_one()
    return MeOut.model_validate({"user": user, "organization": org}, from_attributes=True)
