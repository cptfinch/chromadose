"""Tests for the CLI module."""

import tempfile
from pathlib import Path

import numpy as np

from chromadose.cli import main


class TestCLI:
    def test_no_args_prints_help(self) -> None:
        """Running with no args should return 0 (help displayed)."""
        result = main([])
        assert result == 0

    def test_version(self) -> None:
        """--version should exit cleanly."""
        try:
            main(["--version"])
        except SystemExit as e:
            assert e.code == 0

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
