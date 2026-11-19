"""
CivicPilot Main Application.
FastAPI entry point configuring settings, CORS, error formatting,
lifespan startup/shutdown, and API routes.
Source of truth: docs/CONTRACT.md.
"""

import sys
from pathlib import Path

# Ensure repository root and backend directory are in sys.path
# so imports like 'backend.app...' work regardless of how Render or uvicorn is invoked
_app_dir = Path(__file__).resolve().parent
_backend_dir = _app_dir.parent
_repo_root = _backend_dir.parent

for _p in [str(_repo_root), str(_backend_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Pre-load tools so all tools are registered in registry
import backend.app.tools  # noqa: F401
from backend.app.api.approvals import router as approvals_router
from backend.app.api.auth import router as auth_router
from backend.app.api.cases import router as cases_router
from backend.app.api.demo import router as demo_router
from backend.app.api.eval import router as eval_router
from backend.app.api.health import router as health_router
from backend.app.api.sandbox import router as sandbox_router
from backend.app.core.config import get_settings
from backend.app.db.session import init_db_extensions
from backend.app.tools.scheduler import scheduler_worker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle hooks: initialize DB extensions and start background timers."""
    # Startup
    try:
        await init_db_extensions()
    except Exception as e:
        print(f"[Lifespan Warning] init_db_extensions error: {e}")

    scheduler_worker.start()
    yield
    # Shutdown
    await scheduler_worker.stop()


app = FastAPI(
    title="CivicPilot API",
    description="Multi-agent civic grievance resolution system (Perceive, Reason, Plan, Act, Evaluate, Adapt).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

settings = get_settings()

# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------

origins = [
    origin.strip()
    for origin in settings.FRONTEND_ORIGIN.split(",")
    if origin.strip()
]
# Ensure common local dev origins are accepted
if "http://localhost:3000" not in origins:
    origins.append("http://localhost:3000")
if "http://127.0.0.1:3000" not in origins:
    origins.append("http://127.0.0.1:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Consistent Error Format (CONTRACT.md Section 7: {error: {code, message}})
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
            }
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Build clean human-readable message from validation errors
    errors = exc.errors()
    msg = "; ".join(f"{'.'.join(str(loc) for loc in err.get('loc', []))}: {err.get('msg')}" for err in errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": msg or "Invalid request parameters",
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error_id = uuid.uuid4().hex[:8]
    print(f"[Unhandled Server Error {error_id}]: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_server_error",
                "message": f"An unexpected error occurred (Ref: {error_id}): {str(exc)}",
            }
        },
    )


# ---------------------------------------------------------------------------
# Route Registration
# ---------------------------------------------------------------------------

api_prefix = "/api"

app.include_router(cases_router, prefix=api_prefix)
app.include_router(auth_router, prefix=api_prefix)
app.include_router(approvals_router, prefix=api_prefix)
app.include_router(sandbox_router, prefix=api_prefix)
app.include_router(demo_router, prefix=api_prefix)
app.include_router(eval_router, prefix=api_prefix)
app.include_router(health_router, prefix=api_prefix)

# Also expose /health at root for hosting providers that check root /health
@app.get("/health", include_in_schema=False)
async def root_health():
    from backend.app.api.health import health_check
    return await health_check()
