"""Service layer: bridges HTTP payloads to the chromadose library.

Every function here is deliberately thin — it converts uploaded bytes into the
inputs chromadose expects, calls the tested library, and returns plain Python
objects. All chromadose imports are local so the module imports cheaply and a
missing optional dependency (pydicom) surfaces only when actually used.
"""

from __future__ import annotations

import base64
import io
import json
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

CLI_METHODS = ("micke", "mayer")


@contextmanager
def _temp_file(data: bytes, suffix: str) -> Iterator[Path]:
    """Write bytes to a NamedTemporaryFile and yield its path, cleaning up after."""
    handle = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        handle.write(data)
        handle.flush()
        handle.close()
        yield Path(handle.name)
    finally:
        Path(handle.name).unlink(missing_ok=True)


def _load_npy(data: bytes) -> NDArray[np.floating]:
    """Load a NumPy ``.npy`` payload from bytes (no pickle, arrays only)."""
    array = np.load(io.BytesIO(data), allow_pickle=False)
    return np.asarray(array, dtype=np.float64)


def npy_to_b64(array: NDArray[np.floating]) -> str:
    """Serialize an array to a base64-encoded ``.npy`` blob."""
    buffer = io.BytesIO()
    np.save(buffer, array)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def parse_criteria(criteria: str) -> tuple[float, float]:
    """Parse a ``"3/3"`` dose%/DTA(mm) string, raising ValueError if malformed."""
    parts = criteria.split("/")
    if len(parts) != 2:
        raise ValueError(f"criteria must be 'dose/dta', e.g. '3/3'; got {criteria!r}")
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        raise ValueError(f"criteria values must be numbers; got {criteria!r}") from None


def build_calibration(films: Sequence[bytes], doses: Sequence[float]) -> dict[str, Any]:
    """Build a calibration JSON from calibration film scans and known doses.

    Uses the central 50% of each film as the ROI, matching the CLI.
    """
    from chromadose.calibration import Calibration
    from chromadose.core.image import load_tiff

    if len(films) != len(doses):
        raise ValueError(f"{len(films)} films but {len(doses)} doses")
    if len(films) < 2:
        raise ValueError("at least two calibration films are required")

    with ExitStack() as stack:
        scans = [load_tiff(stack.enter_context(_temp_file(b, ".tif"))) for b in films]
        pixel_values = np.zeros((len(doses), 3))
        for i, film in enumerate(scans):
            h, w = film.shape
            y0, x0, y1, x1 = h // 4, w // 4, 3 * h // 4, 3 * w // 4
            pixel_values[i, 0] = float(np.mean(film.red[y0:y1, x0:x1]))
            pixel_values[i, 1] = float(np.mean(film.green[y0:y1, x0:x1]))
            pixel_values[i, 2] = float(np.mean(film.blue[y0:y1, x0:x1]))

        cal = Calibration.from_arrays(
            doses=np.asarray(doses, dtype=np.float64),
            red_pixels=pixel_values[:, 0],
            green_pixels=pixel_values[:, 1],
            blue_pixels=pixel_values[:, 2],
        )
        out = stack.enter_context(_temp_file(b"", ".json"))
        cal.save(out)
        result: dict[str, Any] = json.loads(out.read_text())
        return result


def solve_dose(film: bytes, calibration: dict[str, Any], method: str) -> dict[str, Any]:
    """Convert a film scan to a dose map using a calibration."""
    if method not in CLI_METHODS:
        raise ValueError(f"unknown method {method!r}; choose from {', '.join(CLI_METHODS)}")

    from chromadose.calibration import Calibration
    from chromadose.core.image import load_tiff
    from chromadose.methods import get_solver

    from app.preview import array_to_png_datauri

    with _temp_file(json.dumps(calibration).encode(), ".json") as cal_path, _temp_file(
        film, ".tif"
    ) as film_path:
        cal = Calibration.load(cal_path)
        scan = load_tiff(film_path)
        result = get_solver(method)().solve(scan, cal.result)

    dose = np.asarray(result.dose, dtype=np.float64)
    return {
        "method": result.method,
        "shape": [int(dose.shape[0]), int(dose.shape[1])],
        "max_dose_gy": float(np.max(dose)),
        "mean_dose_gy": float(np.mean(dose)),
        "mean_uncertainty_gy": float(np.mean(result.uncertainty)),
        "preview_png": array_to_png_datauri(dose, label="Dose (Gy)"),
        "dose_npy_b64": npy_to_b64(dose),
    }


def run_gamma(
    measured: bytes,
    reference: bytes,
    *,
    criteria: str,
    threshold: float,
    pixel_size_mm: float,
) -> dict[str, Any]:
    """Run 2D gamma analysis between a measured and reference dose (.npy)."""
    from chromadose.analysis.gamma import gamma_2d

    from app.preview import array_to_png_datauri

    dose_crit, dta_crit = parse_criteria(criteria)
    meas = _load_npy(measured)
    ref = _load_npy(reference)
    if meas.shape != ref.shape:
        raise ValueError(f"measured {meas.shape} and reference {ref.shape} shapes differ")

    result = gamma_2d(
        ref, meas,
        dose_criteria=dose_crit,
        distance_criteria_mm=dta_crit,
        pixel_size_mm=pixel_size_mm,
        dose_threshold_pct=threshold,
    )
    return {
        "criteria": result.criteria,
        "pass_rate": float(result.pass_rate),
        "pass_rate_pct": round(float(result.pass_rate) * 100.0, 2),
        "points_evaluated": int(result.points_evaluated),
        "points_passed": int(result.points_passed),
        "preview_png": array_to_png_datauri(
            result.gamma_map, label="Gamma index", cmap="RdBu_r", vmin=0.0, vmax=2.0
        ),
    }


def plan_geometry(rtplan: bytes, *, include_setup: bool) -> list[dict[str, Any]]:
    """Read IEC 61217 beam geometry from a DICOM RT Plan."""
    from chromadose.io.dicom import load_beam_geometry

    with _temp_file(rtplan, ".dcm") as path:
        beams = load_beam_geometry(path, include_setup=include_setup)
    return [
        {
            "beam_number": b.beam_number,
            "beam_name": b.beam_name,
            "gantry_angle": b.gantry_angle,
            "collimator_angle": b.collimator_angle,
            "couch_angle": b.couch_angle,
            "beam_energy_mv": b.beam_energy_mv,
            "ssd_mm": b.ssd_mm,
        }
        for b in beams
    ]


def export_rtdose(
    dose: bytes, *, pixel_size_mm: float, patient_name: str, patient_id: str, plan_label: str
) -> bytes:
    """Export a dose map (.npy) to a DICOM RT Dose file, returned as bytes."""
    from chromadose.io.dicom import save_dicom_dose

    array = _load_npy(dose)
    with _temp_file(b"", ".dcm") as out:
        save_dicom_dose(
            array, out,
            pixel_spacing_mm=(pixel_size_mm, pixel_size_mm),
            patient_name=patient_name,
            patient_id=patient_id,
            plan_label=plan_label,
        )
        return out.read_bytes()


def export_sr(
    measured: bytes,
    reference: bytes | None,
    *,
    criteria: str,
    threshold: float,
    pixel_size_mm: float,
    method: str,
    film_type: str,
    patient_name: str,
    patient_id: str,
    plan_label: str,
) -> bytes:
    """Export a QA result to a DICOM Structured Report, returned as bytes."""
    from chromadose.io.dicom_sr import save_dicom_sr

    meas = _load_npy(measured)
    gamma_result = None
    if reference is not None:
        from chromadose.analysis.gamma import gamma_2d

        dose_crit, dta_crit = parse_criteria(criteria)
        gamma_result = gamma_2d(
            _load_npy(reference), meas,
            dose_criteria=dose_crit,
            distance_criteria_mm=dta_crit,
            pixel_size_mm=pixel_size_mm,
            dose_threshold_pct=threshold,
        )

    with _temp_file(b"", ".dcm") as out:
        save_dicom_sr(
            out,
            gamma_result=gamma_result,
            max_dose_gy=float(np.max(meas)),
            mean_dose_gy=float(np.mean(meas)),
            method=method,
            film_type=film_type,
            patient_name=patient_name,
            patient_id=patient_id,
            plan_label=plan_label,
        )
        return out.read_bytes()


def build_report(
    measured: bytes,
    reference: bytes | None,
    *,
    title: str,
    patient_id: str,
    plan_name: str,
) -> bytes:
    """Generate a PDF QA report, returned as bytes."""
    from chromadose.core.types import DoseMap
    from chromadose.io.report import generate_report

    meas = _load_npy(measured)
    ref = _load_npy(reference) if reference is not None else None
    dose_map = DoseMap(
        dose=meas,
        uncertainty=np.zeros_like(meas),
        dose_r=meas,
        dose_g=meas,
        dose_b=meas,
    )
    gamma_result = None
    if ref is not None:
        from chromadose.analysis.gamma import gamma_2d

        gamma_result = gamma_2d(ref, meas)

    with _temp_file(b"", ".pdf") as out:
        generate_report(
            out, dose_map,
            gamma_result=gamma_result,
            reference_dose=ref,
            title=title,
            patient_id=patient_id,
            plan_name=plan_name,
        )
        return out.read_bytes()
