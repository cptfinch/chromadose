"""Tests for the gamma analysis module."""

import numpy as np

from chromadose.analysis.gamma import gamma_2d


class TestGamma2D:
    def test_identical_distributions_pass_100(self) -> None:
        """Identical distributions should give 100% pass rate."""
        dose = np.ones((20, 20)) * 2.0
        result = gamma_2d(dose, dose, dose_criteria=3.0, distance_criteria_mm=3.0)
        assert result.pass_rate == 1.0
        assert result.points_passed == result.points_evaluated

    def test_gamma_zero_for_identical(self) -> None:
        """Gamma should be 0.0 everywhere for identical distributions."""
        dose = np.ones((20, 20)) * 2.0
        result = gamma_2d(dose, dose, dose_criteria=3.0, distance_criteria_mm=3.0)
        valid = result.gamma_map[~np.isnan(result.gamma_map)]
        np.testing.assert_allclose(valid, 0.0, atol=1e-10)

    def test_uniform_dose_difference(self) -> None:
        """A uniform 1% dose difference should pass 3%/3mm."""
        ref = np.ones((30, 30)) * 2.0
        evl = np.ones((30, 30)) * 2.02  # 1% difference
        result = gamma_2d(
            ref, evl, dose_criteria=3.0, distance_criteria_mm=3.0,
            pixel_size_mm=1.0,
        )
        assert result.pass_rate == 1.0

    def test_large_dose_difference_fails(self) -> None:
        """A 5% uniform dose difference should fail 3%/3mm."""
        ref = np.ones((30, 30)) * 2.0
        evl = np.ones((30, 30)) * 2.10  # 5% difference
        result = gamma_2d(
            ref, evl, dose_criteria=3.0, distance_criteria_mm=3.0,
            pixel_size_mm=1.0,
        )
        assert result.pass_rate < 1.0

    def test_shifted_distribution_within_dta(self) -> None:
        """A shifted gradient should pass if shift is within DTA criterion."""
        x = np.arange(50, dtype=np.float64)
        ref = np.broadcast_to(x * 0.1, (20, 50)).copy()  # 0 to 4.9 Gy
        # Shift by 2 pixels = 2mm
        evl = np.zeros_like(ref)
        evl[:, 2:] = ref[:, :-2]
        evl[:, :2] = ref[:, 0:1]

        result = gamma_2d(
            ref, evl, dose_criteria=3.0, distance_criteria_mm=3.0,
            pixel_size_mm=1.0, dose_threshold_pct=10.0,
        )
        # Most points should pass (shift is within 3mm DTA)
        assert result.pass_rate > 0.80

    def test_dose_threshold_excludes_low_dose(self) -> None:
        """Points below threshold should be excluded (NaN in gamma map)."""
        ref = np.zeros((20, 20))
        ref[5:15, 5:15] = 2.0  # Only central region has dose
        evl = ref.copy()

        result = gamma_2d(
            ref, evl, dose_criteria=3.0, distance_criteria_mm=3.0,
            dose_threshold_pct=10.0,
        )
        # Corners should be NaN (below threshold)
        assert np.isnan(result.gamma_map[0, 0])
        # Center should be valid
        assert not np.isnan(result.gamma_map[10, 10])

    def test_shape_mismatch_raises(self) -> None:
        """Mismatched shapes should raise ValueError."""
        ref = np.ones((10, 10))
        evl = np.ones((10, 20))
        try:
            gamma_2d(ref, evl)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_criteria_string(self) -> None:
        """Result should contain a human-readable criteria string."""
        dose = np.ones((10, 10)) * 2.0
        result = gamma_2d(dose, dose, dose_criteria=3.0, distance_criteria_mm=3.0)
        assert "3%/3mm" in result.criteria

    def test_local_dose_criteria(self) -> None:
        """Local dose criteria should use per-point normalization."""
        ref = np.ones((20, 20)) * 2.0
        evl = np.ones((20, 20)) * 2.02
        result = gamma_2d(
            ref, evl, dose_criteria=3.0, distance_criteria_mm=3.0,
            dose_criteria_is_global=False,
        )
        assert "local" in result.criteria
        assert result.pass_rate == 1.0

    def test_metadata_contains_parameters(self) -> None:
        """Metadata should store the analysis parameters."""
        dose = np.ones((10, 10)) * 2.0
        result = gamma_2d(dose, dose, dose_criteria=2.0, distance_criteria_mm=2.0)
        assert result.metadata["dose_criteria_pct"] == 2.0
        assert result.metadata["distance_criteria_mm"] == 2.0
