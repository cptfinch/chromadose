"""Tests for the CLI module."""

import importlib.util
import tempfile
from pathlib import Path

import numpy as np
import pytest
import tifffile

from chromadose import __version__
from chromadose.calibration import Calibration
from chromadose.cli import main
from chromadose.core.types import FitParams

# Realistic EBT3 rational-function parameters: pixel(D) = (r + s*D) / (t + D)
_RED = FitParams(r=0.655, s=0.037, t=2.956)
_GREEN = FitParams(r=0.448, s=0.070, t=10.636)
_BLUE = FitParams(r=0.402, s=0.007, t=5.963)


def _write_synthetic_film(path: Path, doses: np.ndarray) -> None:
    """Write a synthetic RGB float TIFF whose pixels encode a dose grid."""
    rgb = np.stack(
        [_RED.pixel(doses), _GREEN.pixel(doses), _BLUE.pixel(doses)], axis=-1
    ).astype(np.float32)
    tifffile.imwrite(path, rgb, photometric="rgb")


def _write_calibration(path: Path) -> None:
    """Write a calibration JSON matching the synthetic film parameters."""
    doses = np.array([0.0, 0.5, 1.0, 2.0, 4.0, 7.0, 9.0])
    cal = Calibration.from_arrays(
        doses=doses,
        red_pixels=_RED.pixel(doses),
        green_pixels=_GREEN.pixel(doses),
        blue_pixels=_BLUE.pixel(doses),
    )
    cal.save(path)

_HAS_PYDICOM = importlib.util.find_spec("pydicom") is not None


class TestCLI:
    def test_no_args_prints_help(self) -> None:
        """Running with no args should return 0 (help displayed)."""
        result = main([])
        assert result == 0

    def test_version(self, capsys) -> None:  # type: ignore[no-untyped-def]
        """--version should exit cleanly and report the package version."""
        try:
            main(["--version"])
        except SystemExit as e:
            assert e.code == 0
        out = capsys.readouterr().out
        assert __version__ in out

    def test_gamma_command(self) -> None:
        """Gamma command should work with synthetic data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ref_path = str(Path(tmpdir) / "ref.npy")
            meas_path = str(Path(tmpdir) / "meas.npy")
            out_path = str(Path(tmpdir) / "gamma.npy")

            ref = np.ones((20, 20)) * 2.0
            meas = np.ones((20, 20)) * 2.02
            np.save(ref_path, ref)
            np.save(meas_path, meas)

            result = main([
                "gamma",
                "--measured", meas_path,
                "--reference", ref_path,
                "--criteria", "3/3",
                "-o", out_path,
            ])
            assert result == 0
            assert Path(out_path).exists()

    def test_report_command(self) -> None:
        """Report command should create a PDF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            meas_path = str(Path(tmpdir) / "dose.npy")
            out_path = str(Path(tmpdir) / "report.pdf")

            dose = np.ones((20, 20)) * 2.0
            np.save(meas_path, dose)

            result = main([
                "report",
                "--measured", meas_path,
                "--title", "Test Report",
                "-o", out_path,
            ])
            assert result == 0
            assert Path(out_path).exists()

    def test_batch_qa_without_reference(self) -> None:
        """batch-qa should solve every film and write per-film dose + summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            cal_path = tmp / "cal.json"
            _write_calibration(cal_path)

            doses = np.broadcast_to(np.linspace(0, 5, 12), (12, 12))
            films = []
            for i in range(2):
                fp = tmp / f"film{i}.tif"
                _write_synthetic_film(fp, doses)
                films.append(str(fp))

            outdir = tmp / "out"
            result = main(["batch-qa", *films, "--cal", str(cal_path), "--outdir", str(outdir)])

            assert result == 0
            assert (outdir / "film0_dose.npy").exists()
            assert (outdir / "film1_dose.npy").exists()
            assert (outdir / "summary.csv").exists()
            # Recovered dose should be close to the encoded dose grid.
            recovered = np.load(outdir / "film0_dose.npy")
            assert np.allclose(recovered, doses, atol=0.1)

    def test_batch_qa_with_npy_reference(self) -> None:
        """batch-qa with a reference should run gamma and record the pass rate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            cal_path = tmp / "cal.json"
            _write_calibration(cal_path)

            doses = np.broadcast_to(np.linspace(0, 5, 12), (12, 12))
            film_path = tmp / "film.tif"
            _write_synthetic_film(film_path, doses)

            # Reference identical to the encoded dose -> high gamma pass rate.
            ref_path = tmp / "ref.npy"
            np.save(ref_path, np.asarray(doses, dtype=float))

            outdir = tmp / "out"
            result = main([
                "batch-qa", str(film_path),
                "--cal", str(cal_path),
                "--ref", str(ref_path),
                "--criteria", "3/3",
                "--pixel-size", "0.353",
                "--outdir", str(outdir),
            ])

            assert result == 0
            assert (outdir / "film_gamma.npy").exists()
            summary = (outdir / "summary.csv").read_text()
            assert "gamma_pass_rate_pct" in summary
            # Last column of the data row should be a populated pass rate.
            pass_rate = float(summary.strip().splitlines()[1].split(",")[-1])
            assert pass_rate > 95.0

    def test_batch_qa_continues_on_bad_film(self) -> None:
        """A film that fails to process is recorded but does not abort the batch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            cal_path = tmp / "cal.json"
            _write_calibration(cal_path)

            doses = np.broadcast_to(np.linspace(0, 5, 12), (12, 12))
            good = tmp / "good.tif"
            _write_synthetic_film(good, doses)
            bad = tmp / "bad.tif"
            bad.write_text("not a tiff")  # will fail to load

            outdir = tmp / "out"
            result = main([
                "batch-qa", str(bad), str(good),
                "--cal", str(cal_path), "--outdir", str(outdir),
            ])

            # Non-zero because one film failed, but the good film still ran.
            assert result == 1
            assert (outdir / "good_dose.npy").exists()
            assert not (outdir / "bad_dose.npy").exists()
            rows = (outdir / "summary.csv").read_text().strip().splitlines()
            assert rows[1] == "bad,,,"  # failed film recorded with empty metrics
            assert rows[2].startswith("good,")

    def test_batch_qa_bad_reference_is_fatal(self) -> None:
        """A reference that cannot be loaded fails fast before processing films."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            cal_path = tmp / "cal.json"
            _write_calibration(cal_path)
            film = tmp / "film.tif"
            _write_synthetic_film(film, np.broadcast_to(np.linspace(0, 5, 12), (12, 12)))

            result = main([
                "batch-qa", str(film),
                "--cal", str(cal_path),
                "--ref", str(tmp / "missing.npy"),
                "--outdir", str(tmp / "out"),
            ])
            assert result == 1

    @pytest.mark.skipif(not _HAS_PYDICOM, reason="pydicom not installed")
    def test_export_dicom_command(self) -> None:
        """export-dicom should write a loadable RT Dose file."""
        from chromadose.io.dicom import load_dicom_dose

        with tempfile.TemporaryDirectory() as tmpdir:
            dose_path = str(Path(tmpdir) / "dose.npy")
            out_path = str(Path(tmpdir) / "dose.dcm")

            dose = np.linspace(0, 5, 400).reshape(20, 20)
            np.save(dose_path, dose)

            result = main([
                "export-dicom",
                "--dose", dose_path,
                "--pixel-size", "0.353",
                "--plan", "QA",
                "-o", out_path,
            ])
            assert result == 0
            assert Path(out_path).exists()

            rt = load_dicom_dose(out_path)
            np.testing.assert_allclose(rt.slice_2d(0), dose, atol=1e-5)
            assert rt.pixel_spacing_mm == (0.353, 0.353)

    @pytest.mark.skipif(not _HAS_PYDICOM, reason="pydicom not installed")
    def test_export_sr_command(self) -> None:
        """export-sr should write a readable DICOM SR with the gamma metrics."""
        from chromadose.io.dicom_sr import read_dicom_sr

        with tempfile.TemporaryDirectory() as tmpdir:
            meas_path = str(Path(tmpdir) / "dose.npy")
            ref_path = str(Path(tmpdir) / "ref.npy")
            out_path = str(Path(tmpdir) / "qa_sr.dcm")

            ref = np.ones((20, 20)) * 2.0
            np.save(meas_path, ref + 0.01)
            np.save(ref_path, ref)

            result = main([
                "export-sr",
                "--measured", meas_path,
                "--reference", ref_path,
                "--criteria", "3/3",
                "--method", "micke",
                "-o", out_path,
            ])
            assert result == 0
            assert Path(out_path).exists()

            values = read_dicom_sr(out_path)
            assert values["Dosimetry method"] == "micke"
            assert "Gamma pass rate" in values
            assert values["Maximum dose"] == pytest.approx(2.01, abs=1e-3)

    @pytest.mark.skipif(not _HAS_PYDICOM, reason="pydicom not installed")
    def test_export_sr_with_rtplan_geometry(self) -> None:
        """export-sr --rtplan records the plan's beam geometry in the SR."""
        from chromadose.io.dicom_sr import read_dicom_sr

        from .test_geometry import _write_rtplan

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            meas_path = str(tmp / "dose.npy")
            plan_path = tmp / "plan.dcm"
            out_path = str(tmp / "qa_sr.dcm")

            np.save(meas_path, np.ones((20, 20)) * 2.0)
            _write_rtplan(plan_path, [
                {"number": 1, "name": "LLAT", "gantry": 90.0, "collimator": 45.0, "couch": 10.0},
            ])

            result = main([
                "export-sr", "--measured", meas_path,
                "--rtplan", str(plan_path), "-o", out_path,
            ])
            assert result == 0
            values = read_dicom_sr(out_path)
            assert values["Gantry angle"] == pytest.approx(90.0)
            assert values["Beam name"] == "LLAT"

    @pytest.mark.skipif(not _HAS_PYDICOM, reason="pydicom not installed")
    def test_plan_geometry_command(self, capsys) -> None:  # type: ignore[no-untyped-def]
        """plan-geometry should list beam angles from an RT Plan."""
        from .test_geometry import _write_rtplan

        with tempfile.TemporaryDirectory() as tmpdir:
            plan = Path(tmpdir) / "plan.dcm"
            _write_rtplan(plan, [
                {"number": 1, "name": "AP", "gantry": 0.0, "collimator": 0.0, "couch": 0.0},
                {"number": 2, "name": "LLAT", "gantry": 90.0, "collimator": 45.0, "couch": 10.0},
            ])

            result = main(["plan-geometry", "--plan", str(plan)])
            assert result == 0
            out = capsys.readouterr().out
            assert "2 beam(s)" in out
            assert "LLAT" in out
            assert "90.0" in out
