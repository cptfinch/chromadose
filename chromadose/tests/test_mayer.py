"""Tests for the Mayer et al. (2012) analytical dose solver."""

import numpy as np

from chromadose.core.types import CalibrationResult, FilmScan
from chromadose.methods.mayer import MayerSolver

from .conftest import KNOWN_RED, KNOWN_GREEN, KNOWN_BLUE


class TestMayerSolver:
    def test_recovers_known_doses(
        self, synthetic_film: FilmScan, synthetic_cal_result: CalibrationResult
    ) -> None:
        """Solver should recover known doses from noiseless synthetic data."""
        solver = MayerSolver()
        dose_map = solver.solve(synthetic_film, synthetic_cal_result)

        expected_doses = np.linspace(0, 5, 10)
        actual = dose_map.dose[5, :]
        np.testing.assert_allclose(actual, expected_doses, atol=0.1)

    def test_method_name(
        self, synthetic_film: FilmScan, synthetic_cal_result: CalibrationResult
    ) -> None:
        solver = MayerSolver()
        result = solver.solve(synthetic_film, synthetic_cal_result)
        assert result.method == "mayer"

    def test_has_disturbance_map(
        self, synthetic_film: FilmScan, synthetic_cal_result: CalibrationResult
    ) -> None:
        solver = MayerSolver()
        result = solver.solve(synthetic_film, synthetic_cal_result)
        assert "disturbance" in result.metadata
        assert result.metadata["disturbance"].shape == synthetic_film.shape

    def test_has_residual_error(
        self, synthetic_film: FilmScan, synthetic_cal_result: CalibrationResult
    ) -> None:
        solver = MayerSolver()
        result = solver.solve(synthetic_film, synthetic_cal_result)
        assert "residual_error" in result.metadata
        # For noiseless data, residual should be near zero
        assert np.mean(result.metadata["residual_error"]) < 0.1

    def test_agrees_with_micke(
        self, synthetic_film: FilmScan, synthetic_cal_result: CalibrationResult
    ) -> None:
        """Mayer and Micke should give very similar results on clean data."""
        from chromadose.methods.micke import MickeSolver

        mayer = MayerSolver().solve(synthetic_film, synthetic_cal_result)
        micke = MickeSolver().solve(synthetic_film, synthetic_cal_result)

        # Should agree within 5% for most pixels
        relative_diff = np.abs(mayer.dose - micke.dose) / np.where(micke.dose > 0.1, micke.dose, 1)
        assert np.median(relative_diff) < 0.05

    def test_noisy_data(self, synthetic_cal_result: CalibrationResult) -> None:
        """With small noise, recovered dose should still be close."""
        rng = np.random.default_rng(42)
        doses = np.linspace(0.5, 5, 10)
        dose_grid = np.broadcast_to(doses, (10, 10))

        red = KNOWN_RED.pixel(dose_grid) + rng.normal(0, 0.003, (10, 10))
        green = KNOWN_GREEN.pixel(dose_grid) + rng.normal(0, 0.003, (10, 10))
        blue = KNOWN_BLUE.pixel(dose_grid) + rng.normal(0, 0.003, (10, 10))

        film = FilmScan(red=red, green=green, blue=blue)
        solver = MayerSolver()
        result = solver.solve(film, synthetic_cal_result)

        # Mayer method can be more sensitive to noise due to the
        # derivative-based approach, so allow 20% median error
        relative_error = np.abs(result.dose[5, :] - doses) / doses
        assert np.median(relative_error) < 0.20
