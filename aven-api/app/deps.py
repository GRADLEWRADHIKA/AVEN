import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ROLE_RANK, Role, User
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate the request and pin the database session to the user's organization.

    The user is re-read from the database on every request, so deactivating a user or
    changing their role takes effect immediately, not when their token expires.
    """
    if credentials is None:
        raise _unauthorized()
    try:
        claims = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise _unauthorized() from None

    # Deliberately unscoped: we do not know the organization until we have found the user.
    user = db.execute(
        select(User).where(User.id == user_id).execution_options(skip_tenant_filter=True)
    ).scalar_one_or_none()

    if user is None or not user.is_active or str(user.org_id) != claims["org"]:
        raise _unauthorized()

    db.info["org_id"] = user.org_id  # from here on, every query is limited to this org
    return user


def require_role(minimum: Role) -> Callable[[User], User]:
    """Dependency factory: allow the request only for users with at least `minimum` role."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if ROLE_RANK[user.role] < ROLE_RANK[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to do this")
        return user

    return checker
