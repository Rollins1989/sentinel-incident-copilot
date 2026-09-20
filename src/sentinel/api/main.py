from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sentinel.api.routers import ask, feedback, health, ingest, metrics
from sentinel.config import settings
from sentinel.observability.tracing import get_logger, set_trace_id

log = get_logger("api")

app = FastAPI(
    title=settings.app_name,
    description="Production-style engineering knowledge copilot for grounded incident response.",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Sentinel-Admin-Token", "X-Request-ID"],
)

@app.middleware("http")
async def request_context(request: Request, call_next):
    trace_id = request.headers.get("X-Request-ID") or uuid4().hex[:12]
    set_trace_id(trace_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = trace_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    log.info("http.request", extra={"path": request.url.path, "method": request.method, "status_code": response.status_code})
    return response

app.include_router(health.router, tags=["health"])
app.include_router(ask.router, tags=["ask"])
app.include_router(ingest.router, tags=["ingest"])
app.include_router(feedback.router, tags=["feedback"])
app.include_router(metrics.router, tags=["metrics"])

_frontend_dir = Path(__file__).resolve().parents[3] / "frontend"
if _frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(str(_frontend_dir / "index.html"))
