import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import tenancy  # noqa: F401  (importing registers the tenant filter and write guards)
from app.config import get_settings
from app.db import engine
from app.routers import audit_logs, auth, practices, users

settings = get_settings()
logger = logging.getLogger("aven")

app = FastAPI(
    title="AVEN API",
    version="0.1.0",
    docs_url=None if settings.env == "production" else "/docs",
    redoc_url=None,
    openapi_url=None if settings.env == "production" else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(tenancy.TenantContextError)
async def tenant_error_handler(request: Request, exc: tenancy.TenantContextError) -> JSONResponse:
    # A bug, never a normal condition: log it loudly and reveal nothing to the caller.
    logger.error("Tenant isolation guard triggered on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse({"detail": "Internal error"}, status_code=500)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
def ready() -> dict[str, str]:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ready"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(practices.router)
app.include_router(audit_logs.router)
