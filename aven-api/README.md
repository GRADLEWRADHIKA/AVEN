# aven-api

AVEN backend: FastAPI, PostgreSQL, SQLAlchemy, Alembic.

See the main [README](../README.md) for how to run everything and what the rules are.

```
app/
  main.py        app setup and routers
  config.py      settings from environment variables
  db.py          database connection
  models.py      tables (TenantMixin marks organization-owned data)
  tenancy.py     automatic organization isolation and audit-log protection
  security.py    password hashing and tokens
  deps.py        "who is signed in" and role checks
  audit.py       helper for writing audit entries
  routers/       endpoints: auth, users, practices, audit logs
migrations/      database migrations (Alembic)
tests/           automated tests
scripts/         check_no_phi.py and the git hook installer
```

Quick start without Docker for the API:

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload     # docs at http://localhost:8000/docs
pytest
```

Adding a new customer-data table: inherit `TenantMixin`, create `uuid` ids in code (`id=uuid.uuid4()`), generate a migration, and add a test showing one organization cannot read another's rows.
