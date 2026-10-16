"""Automatic multi-tenancy.

How it works
------------
* Each request's database session carries `session.info["org_id"]`, set once the user is
  authenticated (see deps.get_current_user).
* READS: every SELECT that touches a tenant-scoped model (anything using TenantMixin) gets
  `WHERE org_id = <session org>` added automatically.
* WRITES: any new or changed tenant-scoped row must belong to the session's org, or the flush
  fails. Rows created without an org_id get the session's org filled in.
* FAIL CLOSED: touching tenant data with no org on the session raises TenantContextError
  instead of silently returning everyone's data. The few places that legitimately need to
  look across orgs (login, token lookup) must opt out explicitly with
  `.execution_options(skip_tenant_filter=True)`.
* AUDIT LOGS are append-only: updating or deleting one raises.
"""

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.models import AuditLog, TenantMixin


class TenantContextError(RuntimeError):
    """Raised when tenant data is touched without a valid organization context."""


def _touches_tenant_models(state) -> bool:
    return any(issubclass(mapper.class_, TenantMixin) for mapper in state.all_mappers)


@event.listens_for(Session, "do_orm_execute")
def _scope_queries(state) -> None:
    if state.execution_options.get("skip_tenant_filter"):
        return
    if not (state.is_select or state.is_update or state.is_delete):
        return
    if not _touches_tenant_models(state):
        return

    org_id = state.session.info.get("org_id")
    if org_id is None:
        raise TenantContextError("Query on tenant data without an organization context")

    if state.is_update or state.is_delete:
        # Bulk UPDATE/DELETE bypasses the object-level write guard, so it is not allowed.
        # Load the objects and change them through the session instead.
        raise TenantContextError("Bulk update/delete of tenant data is not allowed; use ORM objects")

    state.statement = state.statement.options(
        with_loader_criteria(
            TenantMixin,
            lambda cls: cls.org_id == org_id,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def _guard_writes(session: Session, flush_context, instances) -> None:
    org_id = session.info.get("org_id")

    for obj in list(session.new) + list(session.dirty):
        if not isinstance(obj, TenantMixin):
            continue
        if org_id is None:
            raise TenantContextError("Write to tenant data without an organization context")
        if obj.org_id is None:
            obj.org_id = org_id
        elif obj.org_id != org_id:
            raise TenantContextError("Cross-organization write blocked")

    for obj in session.deleted:
        if isinstance(obj, TenantMixin):
            if org_id is None or obj.org_id != org_id:
                raise TenantContextError("Cross-organization delete blocked")

    for obj in session.dirty:
        if isinstance(obj, AuditLog) and session.is_modified(obj):
            raise TenantContextError("Audit log entries are append-only")
    for obj in session.deleted:
        if isinstance(obj, AuditLog):
            raise TenantContextError("Audit log entries are append-only")
