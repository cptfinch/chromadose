"""Tests for the Micke et al. (2011) dose solver."""

import numpy as np

from chromadose.core.types import CalibrationResult, FilmScan
from chromadose.methods.micke import MickeSolver

from .conftest import KNOWN_RED, KNOWN_GREEN, KNOWN_BLUE


class TestMickeSolver:
    def test_recovers_known_doses(
        self, synthetic_film: FilmScan, synthetic_cal_result: CalibrationResult
    ) -> None:
        """Solver should recover the known doses from noiseless synthetic data."""
        solver = MickeSolver()
        dose_map = solver.solve(synthetic_film, synthetic_cal_result)

        # The synthetic film has doses from 0 to 5 Gy across columns
        expected_doses = np.linspace(0, 5, 10)

        # Check middle row
        actual = dose_map.dose[5, :]
        np.testing.assert_allclose(actual, expected_doses, atol=0.05)

    def test_method_name(
        self, synthetic_film: FilmScan, synthetic_cal_result: CalibrationResult
    ) -> None:
        solver = MickeSolver()
        result = solver.solve(synthetic_film, synthetic_cal_result)
        assert result.method == "micke"

    def test_uncertainty_is_small_for_consistent_data(
        self, synthetic_film: FilmScan, synthetic_cal_result: CalibrationResult
    ) -> None:
        """With noiseless data, all channels agree, so uncertainty should be near zero."""
        solver = MickeSolver()
        result = solver.solve(synthetic_film, synthetic_cal_result)
        # Uncertainty is std of channel doses — should be very small for perfect data
        assert np.mean(result.uncertainty) < 0.1

    def test_noisy_data(self, synthetic_cal_result: CalibrationResult) -> None:
        """With small noise, recovered dose should still be close."""
        rng = np.random.default_rng(42)
        doses = np.linspace(0.5, 5, 10)
        dose_grid = np.broadcast_to(doses, (10, 10))

        red = KNOWN_RED.pixel(dose_grid) + rng.normal(0, 0.003, (10, 10))
        green = KNOWN_GREEN.pixel(dose_grid) + rng.normal(0, 0.003, (10, 10))
        blue = KNOWN_BLUE.pixel(dose_grid) + rng.normal(0, 0.003, (10, 10))

        film = FilmScan(red=red, green=green, blue=blue)
        solver = MickeSolver()
        result = solver.solve(film, synthetic_cal_result)

        # Should be within 5% for most pixels
        relative_error = np.abs(result.dose[5, :] - doses) / doses
        assert np.median(relative_error) < 0.05

    def test_per_channel_doses_shape(
        self, synthetic_film: FilmScan, synthetic_cal_result: CalibrationResult
    ) -> None:
        solver = MickeSolver()
        result = solver.solve(synthetic_film, synthetic_cal_result)
        assert result.dose_r.shape == synthetic_film.shape
        assert result.dose_g.shape == synthetic_film.shape
        assert result.dose_b.shape == synthetic_film.shape
        assert result.dose.shape == synthetic_film.shape
