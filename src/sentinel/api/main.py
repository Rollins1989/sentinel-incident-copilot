from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sentinel.api.routers import ask, feedback, health, ingest
from sentinel.observability.tracing import get_logger

log = get_logger("api")

app = FastAPI(
    title="Sentinel",
    description="Engineering knowledge copilot for incident response, backed by hybrid RAG over runbooks, postmortems, and API docs.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    log.info(
        "http.request",
        extra={"path": request.url.path, "method": request.method, "status_code": response.status_code},
    )
    return response


app.include_router(health.router, tags=["health"])
app.include_router(ask.router, tags=["ask"])
app.include_router(ingest.router, tags=["ingest"])
app.include_router(feedback.router, tags=["feedback"])

_frontend_dir = Path(__file__).resolve().parents[3] / "frontend"
if _frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")

    @app.get("/")
    def root():
        return FileResponse(str(_frontend_dir / "index.html"))
