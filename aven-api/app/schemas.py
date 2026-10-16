import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Role

PASSWORD_MIN = 12


def _clean(value: str) -> str:
    return " ".join(value.split())


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth -------------------------------------------------------------------------------
class RegisterOrganizationIn(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    admin_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN, max_length=128)

    _clean_names = field_validator("organization_name", "admin_name")(_clean)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


# ---- users and organizations -------------------------------------------------------------
class UserOut(_Out):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    org_id: uuid.UUID
    created_at: datetime


class OrganizationOut(_Out):
    id: uuid.UUID
    name: str


class MeOut(BaseModel):
    user: UserOut
    organization: OrganizationOut


class UserCreateIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=PASSWORD_MIN, max_length=128)
    role: Role = Role.biller

    _clean_name = field_validator("full_name")(_clean)


class UserUpdateIn(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


# ---- practices ---------------------------------------------------------------------------
class PracticeIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    specialty: str | None = Field(default=None, max_length=100)

    _clean_name = field_validator("name")(_clean)


class PracticeOut(_Out):
    id: uuid.UUID
    name: str
    specialty: str | None
    created_at: datetime


# ---- audit -------------------------------------------------------------------------------
class AuditLogOut(_Out):
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    detail: dict | None
    created_at: datetime
