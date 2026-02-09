"""Tests for the dose profiles module."""

import numpy as np

from chromadose.analysis.profiles import (
    DoseProfile,
    compare_profiles,
    extract_col_profile,
    extract_line_profile,
    extract_row_profile,
)


class TestDoseProfile:
    def test_max_dose(self) -> None:
        pos = np.array([0.0, 1.0, 2.0, 3.0])
        dose = np.array([1.0, 2.0, 3.0, 2.0])
        p = DoseProfile(position_mm=pos, dose=dose)
        assert p.max_dose == 3.0

    def test_length_mm(self) -> None:
        pos = np.array([0.0, 1.0, 2.0, 5.0])
        dose = np.ones(4)
        p = DoseProfile(position_mm=pos, dose=dose)
        assert p.length_mm == 5.0

    def test_interpolation(self) -> None:
        pos = np.array([0.0, 1.0, 2.0, 3.0])
        dose = np.array([0.0, 1.0, 2.0, 3.0])
        p = DoseProfile(position_mm=pos, dose=dose)
        interp = p.interpolated(np.array([0.5, 1.5, 2.5]))
        np.testing.assert_allclose(interp, [0.5, 1.5, 2.5])


class TestExtractProfiles:
    def test_row_profile(self) -> None:
        dose = np.arange(20, dtype=np.float64).reshape(4, 5)
        p = extract_row_profile(dose, row=2, pixel_size_mm=0.5)
        np.testing.assert_array_equal(p.dose, dose[2, :])
        assert len(p.position_mm) == 5
        np.testing.assert_allclose(p.position_mm, [0, 0.5, 1.0, 1.5, 2.0])

    def test_col_profile(self) -> None:
        dose = np.arange(20, dtype=np.float64).reshape(4, 5)
        p = extract_col_profile(dose, col=3, pixel_size_mm=1.0)
        np.testing.assert_array_equal(p.dose, dose[:, 3])
        assert len(p.position_mm) == 4

    def test_line_profile_horizontal(self) -> None:
        """A horizontal line profile should match a row profile."""
        dose = np.arange(50, dtype=np.float64).reshape(5, 10)
        p = extract_line_profile(
            dose, start=(2.0, 0.0), end=(2.0, 9.0),
            n_points=10, pixel_size_mm=1.0,
        )
        # Should approximate dose[2, :] closely
        np.testing.assert_allclose(p.dose, dose[2, :], atol=0.01)

    def test_line_profile_length(self) -> None:
        dose = np.ones((10, 10))
        p = extract_line_profile(
            dose, start=(0.0, 0.0), end=(9.0, 0.0),
            n_points=100, pixel_size_mm=0.5,
        )
        # Length should be 9 pixels * 0.5 mm/px = 4.5 mm
        np.testing.assert_allclose(p.length_mm, 4.5, atol=0.1)

    def test_row_profile_label(self) -> None:
        dose = np.ones((5, 5))
        p = extract_row_profile(dose, row=2, pixel_size_mm=1.0)
        assert "Row 2" in p.label

    def test_custom_label(self) -> None:
        dose = np.ones((5, 5))
        p = extract_row_profile(dose, row=0, label="Crossline")
        assert p.label == "Crossline"


class TestCompareProfiles:
    def test_identical_profiles(self) -> None:
        pos = np.linspace(0, 10, 50)
        dose = np.sin(pos) + 2.0
        ref = DoseProfile(position_mm=pos, dose=dose, label="TPS")
        evl = DoseProfile(position_mm=pos, dose=dose, label="Film")
        comp = compare_profiles(ref, evl)
        assert comp.mean_abs_diff_pct < 0.01
        assert comp.max_abs_diff_pct < 0.01

    def test_offset_profiles(self) -> None:
        pos = np.linspace(0, 10, 50)
        dose_ref = np.ones(50) * 2.0
        dose_evl = np.ones(50) * 2.06  # 3% of max (2.0)
        ref = DoseProfile(position_mm=pos, dose=dose_ref, label="TPS")
        evl = DoseProfile(position_mm=pos, dose=dose_evl, label="Film")
        comp = compare_profiles(ref, evl)
        np.testing.assert_allclose(comp.mean_abs_diff_pct, 3.0, atol=0.1)

    def test_diff_shape(self) -> None:
        pos = np.linspace(0, 10, 50)
        dose = np.ones(50) * 2.0
        ref = DoseProfile(position_mm=pos, dose=dose, label="TPS")
        evl = DoseProfile(position_mm=pos, dose=dose, label="Film")
        comp = compare_profiles(ref, evl)
        assert comp.dose_diff.shape == (50,)
        assert comp.dose_diff_pct.shape == (50,)
