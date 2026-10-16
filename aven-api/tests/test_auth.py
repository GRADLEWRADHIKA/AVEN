import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings
from tests.conftest import PASSWORD, add_user, auth, register


def test_register_login_and_me(client):
    token = register(client, "Alpha Billing", "Admin@Alpha-Billing.com")  # email is case-insensitive

    me = client.get("/me", headers=auth(token))
    assert me.status_code == 200
    body = me.json()
    assert body["user"]["email"] == "admin@alpha-billing.com"
    assert body["user"]["role"] == "admin"
    assert body["organization"]["name"] == "Alpha Billing"
    assert "password" not in str(body)

    login = client.post("/auth/login", json={"email": "ADMIN@alpha-billing.com", "password": PASSWORD})
    assert login.status_code == 200
    assert client.get("/me", headers=auth(login.json()["access_token"])).status_code == 200


def test_short_password_is_rejected(client):
    r = client.post(
        "/auth/register-organization",
        json={
            "organization_name": "Alpha",
            "admin_name": "A",
            "email": "a@alpha-billing.com",
            "password": "short",
        },
    )
    assert r.status_code == 422


def test_duplicate_email_is_rejected_across_organizations(client, org_a):
    r = client.post(
        "/auth/register-organization",
        json={
            "organization_name": "Other Org",
            "admin_name": "Someone",
            "email": "admin@alpha-billing.com",
            "password": PASSWORD,
        },
    )
    assert r.status_code == 409


def test_wrong_password_and_unknown_user_look_identical(client, org_a):
    wrong = client.post(
        "/auth/login", json={"email": "admin@alpha-billing.com", "password": "not-the-password"}
    )
    unknown = client.post("/auth/login", json={"email": "nobody@alpha-billing.com", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_requests_without_a_valid_token_are_rejected(client, org_a):
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers=auth("garbage")).status_code == 401
    assert client.get("/practices").status_code == 401


def test_expired_token_is_rejected(client, org_a):
    me = client.get("/me", headers=auth(org_a)).json()["user"]
    expired = jwt.encode(
        {"sub": me["id"], "org": me["org_id"], "exp": datetime.now(UTC) - timedelta(minutes=1)},
        get_settings().secret_key,
        algorithm="HS256",
    )
    assert client.get("/me", headers=auth(expired)).status_code == 401


def test_token_with_wrong_organization_claim_is_rejected(client, org_a):
    me = client.get("/me", headers=auth(org_a)).json()["user"]
    forged = jwt.encode(
        {"sub": me["id"], "org": str(uuid.uuid4()), "exp": datetime.now(UTC) + timedelta(minutes=5)},
        get_settings().secret_key,
        algorithm="HS256",
    )
    assert client.get("/me", headers=auth(forged)).status_code == 401


def test_token_signed_with_another_key_is_rejected(client, org_a):
    me = client.get("/me", headers=auth(org_a)).json()["user"]
    forged = jwt.encode(
        {"sub": me["id"], "org": me["org_id"], "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "some-other-key-some-other-key-some-other-key",
        algorithm="HS256",
    )
    assert client.get("/me", headers=auth(forged)).status_code == 401


def test_deactivated_user_loses_access_immediately(client, org_a):
    biller = add_user(client, org_a, "biller@alpha-billing.com", "biller")
    biller_id = client.get("/me", headers=auth(biller)).json()["user"]["id"]
    assert client.get("/me", headers=auth(biller)).status_code == 200

    r = client.patch(f"/users/{biller_id}", headers=auth(org_a), json={"is_active": False})
    assert r.status_code == 200

    assert client.get("/me", headers=auth(biller)).status_code == 401
    assert (
        client.post(
            "/auth/login", json={"email": "biller@alpha-billing.com", "password": PASSWORD}
        ).status_code
        == 401
    )


def test_organization_signup_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "allow_org_signup", False)
    r = client.post(
        "/auth/register-organization",
        json={
            "organization_name": "Alpha",
            "admin_name": "A",
            "email": "a@alpha-billing.com",
            "password": PASSWORD,
        },
    )
    assert r.status_code == 403
