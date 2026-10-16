# AVEN: app and software foundation

This folder holds the starting point for the AVEN web app, in two repos plus one file that runs everything together:

```
aven/
├── docker-compose.yml   runs database + API + web app with one command
├── .env.example         optional settings for docker-compose
├── aven-api/            the backend (Python, FastAPI, PostgreSQL)
└── aven-web/            the frontend (Next.js, React, TypeScript, Tailwind)
```

What works today: create an organization, sign in, three user roles (biller, manager, admin), and a dashboard where each organization sees only its own data. Cases, denials, appeals and the AI connection come next, built on top of this.

## Run it

### Option 1: Docker (easiest)

Install Docker Desktop, then from this folder:

```
docker compose up --build
```

- Web app: http://localhost:3000
- API documentation: http://localhost:8000/docs

The first start takes a few minutes. After that, code changes in either repo reload automatically.

### Option 2: without Docker for the app (database still in Docker)

```
docker compose up db -d                       # just the database

cd aven-api
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head                          # creates the tables
uvicorn app.main:app --reload                 # API on http://localhost:8000

# in a second terminal
cd aven-web
npm install
cp .env.example .env.local
npm run dev                                   # web app on http://localhost:3000
```

### Try it

1. Open http://localhost:3000 and choose **Create an organization**. You become its admin.
2. Add a practice and a few users with different roles. Sign out and sign in as each to see what changes.
3. Create a second organization (use a private/incognito window). It cannot see anything from the first.

## The rules built in

### Roles

| Role | Can do |
| --- | --- |
| biller | View practices (and, later, work on cases) |
| manager | Everything a biller can, plus add practices and see the user list |
| admin | Everything a manager can, plus add/deactivate users and read the audit log |

The API enforces these rules. The web app only hides buttons to match.

### Organization isolation (multi-tenancy)

Every table holding customer data has an `org_id`. `aven-api/app/tenancy.py` then makes isolation automatic:

- Every database read is limited to the signed-in user's organization, even if a developer forgets to filter.
- Writing a row for a different organization is blocked.
- If code touches customer data with no organization set, it fails loudly instead of returning everyone's data.
- Audit log entries can be added but never changed or deleted.

**When you add a new table** (claims, denials, appeals, documents...), give its model `TenantMixin`, like `Practice` in `app/models.py`. That is all it takes to get these protections.

### Other protections

- Passwords are hashed (scrypt), never stored. Minimum 12 characters.
- Login errors don't reveal whether an email exists.
- The sign-in token lives in an HttpOnly cookie, so page scripts can't read it.
- Deactivating a user or changing their role takes effect immediately.
- Key actions (sign-in, creating users and practices, role changes) go in the audit log.

## Patient data rule

**Real patient data never goes on a laptop, in these repos, in chat, or in screenshots.** Use made-up data only. Real data comes later, once the hosting, access controls and agreements (BAAs) are in place.

A safety net helps: `scripts/check_no_phi.py` (in both repos) blocks commits containing X12/835 files, SSN-like numbers, private keys or `.env` files. Turn it on in each repo once:

```
git init                         # if not already a git repo
sh scripts/install-hooks.sh
```

It also runs in CI on every push.

## Everyday commands

| Where | Command | What it does |
| --- | --- | --- |
| aven-api | `pytest` | Run the tests (24 of them, about 3 seconds) |
| aven-api | `ruff check . && ruff format .` | Lint and auto-format |
| aven-api | `alembic revision --autogenerate -m "add claims"` | Create a migration after changing models |
| aven-api | `alembic upgrade head` | Apply migrations |
| aven-web | `npm run typecheck` | Check types |
| aven-web | `npm run format` | Auto-format |
| aven-web | `npm run build` | Production build |

After changing a model, always generate a migration and read the file it creates before committing it.

## What was checked

- All 24 API tests pass (sign-in, role rules, isolation between organizations, audit-log protection).
- The migration runs up, down and up again on a real PostgreSQL 16 database, and matches the models.
- The API and the production build of the web app were run together against PostgreSQL, and 18 browser-style checks passed: sign-in, wrong password, creating practices and users, role-based screens, deactivating a user, sign-out, and isolation between organizations.
- Lint, formatting, type-check and build are clean in both repos.
- **Not run here:** the Docker containers themselves (no Docker engine was available) and the GitHub Actions workflows. The compose file validates, but expect to fix small things the first time you run `docker compose up --build`.

## Known gaps (planned next, not forgotten)

Before any real customer or real data:

- **Rate limiting and account lockout** on login (to stop password guessing).
- **MFA, password reset and SSO** (the plan calls for WorkOS or Auth0 for SSO).
- **Database-level isolation** (PostgreSQL row-level security) as a second layer under the app-level one.
- **Refresh tokens / session revocation.** Tokens currently last 60 minutes.
- **HTTPS, a production secret manager and hosting under a BAA** (AWS), plus `COOKIE_SECURE=true` in production.
- **Turn off open sign-up** (`ALLOW_ORG_SIGNUP=false`) once you onboard customers yourself.
- **Audit-log coverage** for viewing patient data, once that data exists.

## What to build next

1. Agree the AI message format with your AI coworker, then add the case and denial tables (using `TenantMixin`).
2. Synthetic data generator and the mock AI service.
3. The case worklist and case detail pages.
