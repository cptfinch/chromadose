"""End-to-end tests for the chromadose web API using FastAPI's TestClient."""

from __future__ import annotations

import json

import numpy as np
import pytest

from .conftest import (
    HAS_PYDICOM,
    npy_bytes,
    rtplan_bytes,
    uniform_film_bytes,
)

# Doses used to build a synthetic calibration.
_CAL_DOSES = [0.0, 0.5, 1.0, 2.0, 4.0, 7.0, 9.0]


def _calibrate(client) -> dict:  # type: ignore[no-untyped-def]
    files = [
        ("films", (f"cal{i}.tif", uniform_film_bytes(d), "image/tiff"))
        for i, d in enumerate(_CAL_DOSES)
    ]
    resp = client.post(
        "/api/calibrate",
        data={"doses": ",".join(str(d) for d in _CAL_DOSES)},
        files=files,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestMeta:
    def test_health(self, client) -> None:  # type: ignore[no-untyped-def]
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "micke" in body["methods"]


class TestDosimetry:
    def test_calibrate_then_solve(self, client) -> None:  # type: ignore[no-untyped-def]
        cal = _calibrate(client)
        assert "fit_params" in cal and "red" in cal["fit_params"]

        from .conftest import film_bytes

        dose_grid = np.broadcast_to(np.linspace(0, 5, 16), (16, 16)).copy()
        resp = client.post(
            "/api/solve",
            data={"method": "micke"},
            files={
                "film": ("film.tif", film_bytes(dose_grid), "image/tiff"),
                "calibration": ("cal.json", json.dumps(cal).encode(), "application/json"),
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["method"]
        assert body["shape"] == [16, 16]
        assert body["max_dose_gy"] == pytest.approx(5.0, abs=0.2)
        assert body["preview_png"].startswith("data:image/png;base64,")
        assert body["dose_npy_b64"]

    def test_solve_rejects_unknown_method(self, client) -> None:  # type: ignore[no-untyped-def]
        cal = _calibrate(client)
        resp = client.post(
            "/api/solve",
            data={"method": "bogus"},
            files={
                "film": ("film.tif", uniform_film_bytes(2.0), "image/tiff"),
                "calibration": ("cal.json", json.dumps(cal).encode(), "application/json"),
            },
        )
        assert resp.status_code == 422

    def test_gamma(self, client) -> None:  # type: ignore[no-untyped-def]
        ref = np.ones((20, 20)) * 2.0
        meas = ref + 0.01
        resp = client.post(
            "/api/gamma",
            data={"criteria": "3/3", "pixel_size_mm": "0.353"},
            files={
                "measured": ("m.npy", npy_bytes(meas), "application/octet-stream"),
                "reference": ("r.npy", npy_bytes(ref), "application/octet-stream"),
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["pass_rate_pct"] > 95.0
        assert body["points_evaluated"] > 0

    def test_gamma_shape_mismatch(self, client) -> None:  # type: ignore[no-untyped-def]
        resp = client.post(
            "/api/gamma",
            files={
                "measured": ("m.npy", npy_bytes(np.ones((10, 10))), "application/octet-stream"),
                "reference": ("r.npy", npy_bytes(np.ones((12, 12))), "application/octet-stream"),
            },
        )
        assert resp.status_code == 422

    def test_gamma_bad_criteria(self, client) -> None:  # type: ignore[no-untyped-def]
        resp = client.post(
            "/api/gamma",
            data={"criteria": "3"},
            files={
                "measured": ("m.npy", npy_bytes(np.ones((8, 8))), "application/octet-stream"),
                "reference": ("r.npy", npy_bytes(np.ones((8, 8))), "application/octet-stream"),
            },
        )
        assert resp.status_code == 422


@pytest.mark.skipif(not HAS_PYDICOM, reason="pydicom not installed")
class TestDicom:
    def test_plan_geometry(self, client) -> None:  # type: ignore[no-untyped-def]
        plan = rtplan_bytes([
            {"number": 1, "name": "AP", "gantry": 0.0, "collimator": 0.0, "couch": 0.0},
            {"number": 2, "name": "LLAT", "gantry": 90.0, "collimator": 45.0, "couch": 10.0},
        ])
        resp = client.post(
            "/api/plan-geometry",
            files={"rtplan": ("plan.dcm", plan, "application/dicom")},
        )
        assert resp.status_code == 200, resp.text
        beams = resp.json()["beams"]
        assert len(beams) == 2
        assert beams[1]["gantry_angle"] == 90.0
        assert beams[1]["beam_name"] == "LLAT"

    def test_export_rtdose(self, client) -> None:  # type: ignore[no-untyped-def]
        dose = np.linspace(0, 5, 400).reshape(20, 20)
        resp = client.post(
            "/api/export/rtdose",
            data={"pixel_size_mm": "0.353"},
            files={"dose": ("dose.npy", npy_bytes(dose), "application/octet-stream")},
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/dicom"
        # DICOM files carry the "DICM" magic at byte offset 128.
        assert resp.content[128:132] == b"DICM"

    def test_export_sr(self, client) -> None:  # type: ignore[no-untyped-def]
        meas = np.ones((20, 20)) * 2.01
        ref = np.ones((20, 20)) * 2.0
        resp = client.post(
            "/api/export/sr",
            data={"criteria": "3/3", "method": "micke"},
            files={
                "measured": ("m.npy", npy_bytes(meas), "application/octet-stream"),
                "reference": ("r.npy", npy_bytes(ref), "application/octet-stream"),
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.content[128:132] == b"DICM"


class TestReport:
    def test_report_pdf(self, client) -> None:  # type: ignore[no-untyped-def]
        dose = np.ones((20, 20)) * 2.0
        resp = client.post(
            "/api/report",
            data={"title": "Test QA"},
            files={"measured": ("m.npy", npy_bytes(dose), "application/octet-stream")},
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"
