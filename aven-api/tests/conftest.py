import os

# Must be set before the app is imported: tests run on an in-memory SQLite database.
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-test-secret-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(client: TestClient, org_name: str, email: str) -> str:
    """Create an organization with an admin and return the admin's access token."""
    r = client.post(
        "/auth/register-organization",
        json={
            "organization_name": org_name,
            "admin_name": "Admin Person",
            "email": email,
            "password": PASSWORD,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def add_user(client: TestClient, admin_token: str, email: str, role: str) -> str:
    """Create a user with the given role (as the admin) and return that user's access token."""
    r = client.post(
        "/users",
        headers=auth(admin_token),
        json={"email": email, "full_name": f"{role.title()} Person", "password": PASSWORD, "role": role},
    )
    assert r.status_code == 201, r.text
    login = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


@pytest.fixture
def org_a(client):
    return register(client, "Alpha Billing", "admin@alpha-billing.com")


@pytest.fixture
def org_b(client):
    return register(client, "Beta Billing", "admin@beta-billing.com")
