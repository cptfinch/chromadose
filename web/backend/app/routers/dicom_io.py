"""DICOM and report endpoints: plan-geometry, export RT Dose / SR, PDF report.

These depend on the optional pydicom extra; a missing dependency is surfaced as
a clean 400 rather than a 500.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app import services

router = APIRouter(prefix="/api", tags=["dicom"])


def _run(fn, *args, **kwargs):  # type: ignore[no-untyped-def]
    """Call a service function, mapping known errors to HTTP responses."""
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _file_response(data: bytes, filename: str, media_type: str) -> Response:
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/plan-geometry")
async def plan_geometry(
    rtplan: UploadFile = File(..., description="DICOM RT Plan file"),
    include_setup: bool = Form(False, description="Include setup beams"),
) -> dict[str, Any]:
    """List IEC 61217 beam geometry (gantry / collimator / couch) from an RT Plan."""
    beams = _run(services.plan_geometry, await rtplan.read(), include_setup=include_setup)
    return {"beams": beams}


@router.post("/export/rtdose")
async def export_rtdose(
    dose: UploadFile = File(..., description="Dose map (.npy), in Gy"),
    pixel_size_mm: float = Form(1.0),
    patient_name: str = Form(""),
    patient_id: str = Form(""),
    plan_label: str = Form(""),
) -> Response:
    """Export a dose map to a DICOM RT Dose file."""
    data = _run(
        services.export_rtdose, await dose.read(),
        pixel_size_mm=pixel_size_mm, patient_name=patient_name,
        patient_id=patient_id, plan_label=plan_label,
    )
    return _file_response(data, "dose.dcm", "application/dicom")


@router.post("/export/sr")
async def export_sr(
    measured: UploadFile = File(..., description="Measured dose (.npy)"),
    reference: UploadFile | None = File(None, description="Reference dose (.npy); enables gamma"),
    criteria: str = Form("3/3"),
    threshold: float = Form(10.0),
    pixel_size_mm: float = Form(1.0),
    method: str = Form(""),
    film_type: str = Form(""),
    patient_name: str = Form(""),
    patient_id: str = Form(""),
    plan_label: str = Form(""),
) -> Response:
    """Export a QA result to a DICOM Structured Report."""
    ref_bytes = await reference.read() if reference is not None else None
    data = _run(
        services.export_sr, await measured.read(), ref_bytes,
        criteria=criteria, threshold=threshold, pixel_size_mm=pixel_size_mm,
        method=method, film_type=film_type, patient_name=patient_name,
        patient_id=patient_id, plan_label=plan_label,
    )
    return _file_response(data, "qa_sr.dcm", "application/dicom")


@router.post("/report")
async def report(
    measured: UploadFile = File(..., description="Measured dose (.npy)"),
    reference: UploadFile | None = File(None, description="Reference dose (.npy)"),
    title: str = Form("Film Dosimetry QA Report"),
    patient_id: str = Form(""),
    plan_name: str = Form(""),
) -> Response:
    """Generate a PDF QA report."""
    ref_bytes = await reference.read() if reference is not None else None
    data = _run(
        services.build_report, await measured.read(), ref_bytes,
        title=title, patient_id=patient_id, plan_name=plan_name,
    )
    return _file_response(data, "report.pdf", "application/pdf")
