import uuid

import pytest
from sqlalchemy import select, update

from app.models import AuditLog, Organization, Practice
from app.tenancy import TenantContextError
from tests.conftest import add_user, auth

# ---- roles ------------------------------------------------------------------------------


def test_role_permissions(client, org_a):
    manager = add_user(client, org_a, "manager@alpha-billing.com", "manager")
    biller = add_user(client, org_a, "biller@alpha-billing.com", "biller")
    practice = {"name": "Riverside Orthopedics", "specialty": "orthopedics"}

    # Billers can look but not create.
    assert client.post("/practices", headers=auth(biller), json=practice).status_code == 403
    assert client.get("/practices", headers=auth(biller)).status_code == 200
    assert client.get("/users", headers=auth(biller)).status_code == 403
    assert client.get("/audit-logs", headers=auth(biller)).status_code == 403

    # Managers can create practices and list users, but not manage users or read the audit log.
    assert client.post("/practices", headers=auth(manager), json=practice).status_code == 201
    assert client.get("/users", headers=auth(manager)).status_code == 200
    new_user = {
        "email": "x@alpha-billing.com",
        "full_name": "X",
        "password": "correct-horse-battery",
        "role": "biller",
    }
    assert client.post("/users", headers=auth(manager), json=new_user).status_code == 403
    assert client.get("/audit-logs", headers=auth(manager)).status_code == 403

    # Admins can do all of it.
    assert client.post("/users", headers=auth(org_a), json=new_user).status_code == 201
    assert client.get("/audit-logs", headers=auth(org_a)).status_code == 200


def test_admin_cannot_change_their_own_role_or_status(client, org_a):
    me = client.get("/me", headers=auth(org_a)).json()["user"]
    r = client.patch(f"/users/{me['id']}", headers=auth(org_a), json={"role": "biller"})
    assert r.status_code == 400
    r = client.patch(f"/users/{me['id']}", headers=auth(org_a), json={"is_active": False})
    assert r.status_code == 400


def test_role_change_takes_effect_immediately(client, org_a):
    manager = add_user(client, org_a, "manager@alpha-billing.com", "manager")
    manager_id = client.get("/me", headers=auth(manager)).json()["user"]["id"]
    practice = {"name": "Lakeview Behavioral Health"}
    assert client.post("/practices", headers=auth(manager), json=practice).status_code == 201

    client.patch(f"/users/{manager_id}", headers=auth(org_a), json={"role": "biller"})
    assert client.post("/practices", headers=auth(manager), json={"name": "Another"}).status_code == 403


# ---- tenant isolation through the API ---------------------------------------------------


def test_organizations_cannot_see_each_others_practices(client, org_a, org_b):
    a = client.post("/practices", headers=auth(org_a), json={"name": "Alpha Ortho"}).json()
    b = client.post("/practices", headers=auth(org_b), json={"name": "Beta Cardio"}).json()

    a_list = [p["name"] for p in client.get("/practices", headers=auth(org_a)).json()]
    b_list = [p["name"] for p in client.get("/practices", headers=auth(org_b)).json()]
    assert a_list == ["Alpha Ortho"]
    assert b_list == ["Beta Cardio"]

    # Fetching another org's record by its exact id looks the same as a record that does not exist.
    assert client.get(f"/practices/{a['id']}", headers=auth(org_b)).status_code == 404
    assert client.get(f"/practices/{b['id']}", headers=auth(org_a)).status_code == 404
    assert client.get(f"/practices/{uuid.uuid4()}", headers=auth(org_a)).status_code == 404


def test_organizations_cannot_see_or_edit_each_others_users(client, org_a, org_b):
    add_user(client, org_a, "biller@alpha-billing.com", "biller")
    b_user_id = client.get("/me", headers=auth(org_b)).json()["user"]["id"]

    emails = [u["email"] for u in client.get("/users", headers=auth(org_a)).json()]
    assert sorted(emails) == ["admin@alpha-billing.com", "biller@alpha-billing.com"]

    r = client.patch(f"/users/{b_user_id}", headers=auth(org_a), json={"role": "biller"})
    assert r.status_code == 404


def test_same_practice_name_is_allowed_in_different_organizations(client, org_a, org_b):
    assert (
        client.post("/practices", headers=auth(org_a), json={"name": "Main Street Clinic"}).status_code == 201
    )
    assert (
        client.post("/practices", headers=auth(org_b), json={"name": "Main Street Clinic"}).status_code == 201
    )
    assert (
        client.post("/practices", headers=auth(org_a), json={"name": "Main Street Clinic"}).status_code == 409
    )


def test_audit_log_is_per_organization_and_records_actions(client, org_a, org_b):
    client.post("/practices", headers=auth(org_a), json={"name": "Alpha Ortho"})
    client.post("/practices", headers=auth(org_b), json={"name": "Beta Cardio"})

    a_actions = [e["action"] for e in client.get("/audit-logs", headers=auth(org_a)).json()]
    assert "practice.created" in a_actions
    assert "organization.registered" in a_actions
    assert len(a_actions) == 2

    me_b = client.get("/me", headers=auth(org_b)).json()["user"]
    b_entries = client.get("/audit-logs", headers=auth(org_b)).json()
    assert {e["user_id"] for e in b_entries} == {me_b["id"]}


# ---- the tenancy layer itself (defense in depth) -----------------------------------------


def _org_id(db, name: str):
    return db.execute(select(Organization.id).where(Organization.name == name)).scalar_one()


def test_unscoped_query_on_tenant_data_fails_closed(client, org_a, db):
    with pytest.raises(TenantContextError):
        db.execute(select(Practice)).all()


def test_session_scoped_to_one_org_only_sees_that_org(client, org_a, org_b, db):
    client.post("/practices", headers=auth(org_a), json={"name": "Alpha Ortho"})
    client.post("/practices", headers=auth(org_b), json={"name": "Beta Cardio"})

    db.info["org_id"] = _org_id(db, "Alpha Billing")
    assert [p.name for p in db.execute(select(Practice)).scalars()] == ["Alpha Ortho"]

    # Even an explicit filter for the other org's id returns nothing.
    other = _org_id(db, "Beta Billing")
    assert db.execute(select(Practice).where(Practice.org_id == other)).all() == []


def test_cross_organization_write_is_blocked(client, org_a, org_b, db):
    db.info["org_id"] = _org_id(db, "Alpha Billing")
    other = _org_id(db, "Beta Billing")
    db.add(Practice(id=uuid.uuid4(), org_id=other, name="Smuggled Practice"))
    with pytest.raises(TenantContextError):
        db.flush()
    db.rollback()


def test_write_without_organization_context_is_blocked(client, org_a, db):
    db.add(Practice(id=uuid.uuid4(), org_id=uuid.uuid4(), name="Orphan"))
    with pytest.raises(TenantContextError):
        db.flush()
    db.rollback()


def test_org_id_is_filled_in_for_new_rows(client, org_a, db):
    org_id = _org_id(db, "Alpha Billing")
    db.info["org_id"] = org_id
    practice = Practice(id=uuid.uuid4(), name="No Org Given")
    db.add(practice)
    db.flush()
    assert practice.org_id == org_id
    db.rollback()


def test_bulk_update_of_tenant_data_is_refused(client, org_a, db):
    db.info["org_id"] = _org_id(db, "Alpha Billing")
    with pytest.raises(TenantContextError):
        db.execute(update(Practice).values(name="Renamed everywhere"))


def test_audit_log_entries_cannot_be_changed_or_deleted(client, org_a, db):
    db.info["org_id"] = _org_id(db, "Alpha Billing")
    entry = db.execute(select(AuditLog)).scalars().first()
    assert entry is not None

    entry.action = "tampered"
    with pytest.raises(TenantContextError):
        db.flush()
    db.rollback()

    db.delete(db.execute(select(AuditLog)).scalars().first())
    with pytest.raises(TenantContextError):
        db.flush()
    db.rollback()
