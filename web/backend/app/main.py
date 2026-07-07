"""FastAPI application factory for the chromadose web backend.

RESEARCH USE ONLY — NOT A MEDICAL DEVICE. This service exposes the chromadose
library over HTTP for research and method development; it is not intended for
clinical decision-making. See the chromadose DISCLAIMER.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import dicom_io, dosimetry, health


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
    return app


app = create_app()
