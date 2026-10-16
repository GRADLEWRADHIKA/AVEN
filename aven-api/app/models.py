"""Database models.

Tenancy rule: every table that holds customer data inherits TenantMixin (adds org_id).
app/tenancy.py then filters every query and guards every write by the session's org_id,
so a route handler cannot forget to scope its queries.
"""

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy import Uuid as SAUuid
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Role(enum.StrEnum):
    biller = "biller"
    manager = "manager"
    admin = "admin"


# Higher number = more permissions. "manager" can do everything a "biller" can, and so on.
ROLE_RANK: dict[Role, int] = {Role.biller: 1, Role.manager: 2, Role.admin: 3}


class TenantMixin:
    """Marks a model as belonging to one organization."""

    @declared_attr
    def org_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(SAUuid, ForeignKey("organizations.id"), index=True, nullable=False)

    # Declared (never loaded: lazy="raise") so SQLAlchemy knows an organization must be
    # inserted before the rows that belong to it. Without a relationship, the insert order
    # is not guaranteed and PostgreSQL rejects the foreign key.
    @declared_attr
    def organization(cls) -> Mapped["Organization"]:
        return relationship("Organization", lazy="raise")


class Organization(Base):
    """A billing company or practice. This is the tenant itself, so it has no org_id."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(SAUuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class User(TenantMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(SAUuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=20), default=Role.biller)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Practice(TenantMixin, Base):
    """A medical practice served by a billing company. Example tenant-scoped resource;
    claims, denials and appeals will follow the same pattern."""

    __tablename__ = "practices"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_practice_org_name"),)

    id: Mapped[uuid.UUID] = mapped_column(SAUuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    specialty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(TenantMixin, Base):
    """Append-only record of who did what. Never updated or deleted (enforced in tenancy.py)."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(SAUuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(SAUuid, ForeignKey("users.id"), nullable=True)
    user: Mapped["User | None"] = relationship("User", lazy="raise")  # insert order, see TenantMixin
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
