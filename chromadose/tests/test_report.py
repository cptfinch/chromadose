"""Tests for the PDF report generation module."""

import tempfile
from pathlib import Path

import numpy as np

from chromadose.analysis.gamma import gamma_2d
from chromadose.analysis.profiles import (
    DoseProfile,
    compare_profiles,
    extract_row_profile,
)
from chromadose.core.types import DoseMap
from chromadose.io.report import generate_report


def _make_dose_map() -> DoseMap:
    """Create a simple synthetic dose map for testing."""
    x = np.linspace(0, 5, 30)
    dose = np.broadcast_to(x, (20, 30)).copy()
    return DoseMap(
        dose=dose,
        uncertainty=np.abs(dose) * 0.02,
        dose_r=dose * 0.98,
        dose_g=dose * 1.01,
        dose_b=dose * 1.00,
        method="micke",
    )


class TestReport:
    def test_basic_report_creates_file(self) -> None:
        """A basic report with just a dose map should create a PDF."""
        dm = _make_dose_map()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.pdf"
            result = generate_report(path, dm, title="Test Report")
            assert result.exists()
            assert result.stat().st_size > 0

    def test_report_with_gamma(self) -> None:
        """Report with gamma analysis should include gamma page."""
        dm = _make_dose_map()
        ref = dm.dose
        evl = dm.dose * 1.01  # 1% difference
        gamma = gamma_2d(ref, evl, dose_criteria=3.0, distance_criteria_mm=3.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report_gamma.pdf"
            result = generate_report(path, dm, gamma_result=gamma)
            assert result.exists()
            assert result.stat().st_size > 0

    def test_report_with_profiles(self) -> None:
        """Report with profiles should include profiles page."""
        dm = _make_dose_map()
        ref_profile = extract_row_profile(dm.dose, row=10, pixel_size_mm=1.0, label="TPS")
        evl_profile = extract_row_profile(dm.dose * 1.02, row=10, pixel_size_mm=1.0, label="Film")
        comp = compare_profiles(ref_profile, evl_profile)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report_profiles.pdf"
            result = generate_report(path, dm, profiles=[comp])
            assert result.exists()
            assert result.stat().st_size > 0

    def test_full_report(self) -> None:
        """Full report with all sections."""
        dm = _make_dose_map()
        ref = dm.dose
        evl = dm.dose * 1.01
        gamma = gamma_2d(ref, evl, dose_criteria=3.0, distance_criteria_mm=3.0)

        ref_profile = extract_row_profile(dm.dose, row=10, pixel_size_mm=1.0, label="TPS Inline")
        evl_profile = extract_row_profile(evl, row=10, pixel_size_mm=1.0, label="Film Inline")
        comp = compare_profiles(ref_profile, evl_profile)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "full_report.pdf"
            result = generate_report(
                path, dm,
                gamma_result=gamma,
                profiles=[comp],
                reference_dose=ref,
                title="IMRT QA Report",
                patient_id="TEST001",
                plan_name="Head & Neck IMRT",
                analyst="Auto Test",
                notes="Synthetic data for testing",
            )
            assert result.exists()
            assert result.stat().st_size > 1000  # Should be a reasonable size

    def test_report_returns_path(self) -> None:
        """generate_report should return the path to the PDF."""
        dm = _make_dose_map()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.pdf"
            result = generate_report(path, dm)
            assert result == path
