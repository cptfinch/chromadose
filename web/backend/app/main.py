"""FastAPI application factory for the chromadose web backend.

RESEARCH USE ONLY — NOT A MEDICAL DEVICE. This service exposes the chromadose
library over HTTP for research and method development; it is not intended for
clinical decision-making. See the chromadose DISCLAIMER.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import dicom_io, dosimetry, health

# web/backend/app/main.py -> web/frontend. Override with CHROMADOSE_FRONTEND_DIR
# (the Docker image does, because the package is installed into site-packages).
_DEFAULT_FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def _frontend_dir() -> Path | None:
    """The directory holding the static UI, or None if it isn't present."""
    path = Path(os.environ.get("CHROMADOSE_FRONTEND_DIR", _DEFAULT_FRONTEND_DIR))
    return path if (path / "index.html").is_file() else None


def create_app() -> FastAPI:
    app = FastAPI(
        title="chromadose web API",
        version="0.1.0",
        description="HTTP API over the chromadose radiochromic-film dosimetry library.",
    )

    # CORS: comma-separated origins via CHROMADOSE_CORS_ORIGINS, default "*" for
    # local development. Set an explicit allow-list in production.
    origins = os.environ.get("CHROMADOSE_CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(dosimetry.router)
    app.include_router(dicom_io.router)

    # Serve the single-page UI last so it never shadows an /api route. Absent in
    # an API-only deployment, in which case "/" is simply a 404.
    frontend = _frontend_dir()
    if frontend is not None:
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


app = create_app()
