"""Health / metadata endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.services import CLI_METHODS

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health")
def health() -> dict[str, Any]:
    """Liveness probe plus the backing chromadose version and available methods."""
    from chromadose import __version__

    return {
        "status": "ok",
        "chromadose_version": __version__,
        "methods": list(CLI_METHODS),
    }
