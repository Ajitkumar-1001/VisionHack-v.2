"""HTTP surface for RightHook NYC. PRD §19, §20.

One Cloud Run service: FastAPI + engine + static UI in a single container.

`/health` is the binary eligibility gate (§19). It is defined here, imports
nothing from the agent, camera or context layers, and touches no network — §20
requires that Open Data availability cannot affect it. Keep it that way.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

SERVICE_NAME = "righthook-nyc"
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="RightHook NYC",
    description=(
        "Detects potential turning-vehicle conflicts with cyclists and "
        "pedestrians at a single NYC intersection. Heuristic detection — not a "
        "calibrated crash-risk probability."
    ),
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness. §19 build task #1 — the eligibility gate is this endpoint."""
    return {"service": SERVICE_NAME, "status": "healthy"}


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    # The Astro build (frontend/ -> app/static/next/). Asset URLs inside it are
    # absolute (/static/next/_astro/...), so serving it at / just works. The
    # vanilla console remains at /static/index.html — rollback is this one line.
    return FileResponse(STATIC_DIR / "next" / "index.html")


app.include_router(router, prefix="/api")

# Mounted last so it cannot shadow /health or the API router. html=True serves
# directory indexes, which is how the Astro build at /static/next/ resolves.
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")
