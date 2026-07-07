"""Core dosimetry endpoints: calibrate, solve, gamma."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app import services

router = APIRouter(prefix="/api", tags=["dosimetry"])


def _parse_floats(raw: str) -> list[float]:
    """Parse a comma/space-separated list of floats from a form field."""
    tokens = [t for t in raw.replace(",", " ").split() if t]
    try:
        return [float(t) for t in tokens]
    except ValueError:
        raise HTTPException(status_code=422, detail=f"could not parse numbers from {raw!r}") from None


@router.post("/calibrate")
async def calibrate(
    doses: str = Form(..., description="Known doses in Gy, e.g. '0,0.5,1,2,4,7'"),
    films: list[UploadFile] = File(..., description="Calibration film TIFFs, one per dose"),
) -> dict[str, Any]:
    """Build a calibration from calibration film scans and their known doses."""
    dose_values = _parse_floats(doses)
    film_bytes = [await f.read() for f in films]
    try:
        return services.build_calibration(film_bytes, dose_values)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/solve")
async def solve(
    film: UploadFile = File(..., description="Treatment film TIFF"),
    calibration: UploadFile = File(..., description="Calibration JSON from /api/calibrate"),
    method: str = Form("micke", description="Dose solving method: micke or mayer"),
) -> dict[str, Any]:
    """Convert a scanned film to a dose map."""
    try:
        cal = json.loads(await calibration.read())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="calibration is not valid JSON") from exc
    try:
        return services.solve_dose(await film.read(), cal, method)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/gamma")
async def gamma(
    measured: UploadFile = File(..., description="Measured dose (.npy)"),
    reference: UploadFile = File(..., description="Reference dose (.npy)"),
    criteria: str = Form("3/3", description="Dose%/DTA(mm), e.g. '3/3'"),
    threshold: float = Form(10.0, description="Dose threshold (% of max)"),
    pixel_size_mm: float = Form(1.0, description="Pixel size in mm"),
) -> dict[str, Any]:
    """Run 2D gamma analysis between a measured and reference dose distribution."""
    try:
        return services.run_gamma(
            await measured.read(),
            await reference.read(),
            criteria=criteria,
            threshold=threshold,
            pixel_size_mm=pixel_size_mm,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
