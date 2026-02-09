"""Tests for the Multigaussian (Mendez 2018) dose solver."""

import numpy as np

from chromadose.core.types import CalibrationResult, FilmScan
from chromadose.methods.multigaussian import MultigaussianCalibration, MultigaussianSolver

from .conftest import KNOWN_RED, KNOWN_GREEN, KNOWN_BLUE, CALIBRATION_DOSES


def _make_mg_calibration(n_samples: int = 500) -> MultigaussianCalibration:
    """Create a Multigaussian calibration from synthetic data.

    Generates n_samples pixel values at each calibration dose,
    with realistic noise and inter-channel correlations.
    """
    rng = np.random.default_rng(42)
    doses = CALIBRATION_DOSES
    n_doses = len(doses)

    pixel_samples = np.zeros((n_doses, n_samples, 3))
    for i, d in enumerate(doses):
        mean_r = float(KNOWN_RED.pixel(np.array([d]))[0])
        mean_g = float(KNOWN_GREEN.pixel(np.array([d]))[0])
        mean_b = float(KNOWN_BLUE.pixel(np.array([d]))[0])

        mean = [mean_r, mean_g, mean_b]
        # Realistic covariance: channels are correlated (film thickness
        # affects all channels similarly)
        noise = 0.005
        cov = [
            [noise**2, noise**2 * 0.6, noise**2 * 0.3],
            [noise**2 * 0.6, noise**2, noise**2 * 0.4],
            [noise**2 * 0.3, noise**2 * 0.4, noise**2],
        ]
        pixel_samples[i] = rng.multivariate_normal(mean, cov, size=n_samples)

    return MultigaussianCalibration(doses=doses, pixel_samples=pixel_samples)


class TestMultigaussianCalibration:
    def test_construction(self) -> None:
        mg_cal = _make_mg_calibration()
        assert mg_cal.n_doses == 7
        assert mg_cal.n_channels == 3

    def test_mean_interpolation(self) -> None:
        mg_cal = _make_mg_calibration()
        # Mean at a calibration point should match the data
        mu_at_0 = mg_cal.mean_at(0.0)
        expected_r = float(KNOWN_RED.pixel(np.array([0.0]))[0])
        np.testing.assert_allclose(mu_at_0[0], expected_r, atol=0.01)

    def test_mean_interpolation_between_points(self) -> None:
        mg_cal = _make_mg_calibration()
        # Mean at an intermediate dose should be between neighbors
        mu_at_1_5 = mg_cal.mean_at(1.5)
        mu_at_1 = mg_cal.mean_at(1.0)
        mu_at_2 = mg_cal.mean_at(2.0)
        # Red channel should be between the two neighbors
        assert mu_at_1[0] >= mu_at_1_5[0] >= mu_at_2[0]

    def test_covariance_positive_definite(self) -> None:
        mg_cal = _make_mg_calibration()
        for i in range(mg_cal.n_doses):
            eigvals = np.linalg.eigvalsh(mg_cal.covs[i])
            assert np.all(eigvals > 0)


class TestMultigaussianSolver:
    def test_recovers_known_doses_small(self) -> None:
        """Test on a small 3x3 synthetic image."""
        mg_cal = _make_mg_calibration()

        # Build standard calibration for per-channel doses
        from chromadose.calibration import Calibration
        cal = Calibration.from_arrays(
            doses=CALIBRATION_DOSES,
            red_pixels=KNOWN_RED.pixel(CALIBRATION_DOSES),
            green_pixels=KNOWN_GREEN.pixel(CALIBRATION_DOSES),
            blue_pixels=KNOWN_BLUE.pixel(CALIBRATION_DOSES),
        )

        # Small test image: 3x3 with known doses
        test_doses = np.array([0.5, 2.0, 5.0])
        dose_grid = np.broadcast_to(test_doses, (3, 3))

        red = KNOWN_RED.pixel(dose_grid)
        green = KNOWN_GREEN.pixel(dose_grid)
        blue = KNOWN_BLUE.pixel(dose_grid)
        film = FilmScan(red=red, green=green, blue=blue)

        solver = MultigaussianSolver(mg_cal)
        result = solver.solve(film, cal.result)

        assert result.method == "multigaussian"
        # Should recover doses within 10% for this small test
        actual = result.dose[1, :]
        np.testing.assert_allclose(actual, test_doses, rtol=0.10)

    def test_method_name(self) -> None:
        mg_cal = _make_mg_calibration()
        from chromadose.calibration import Calibration
        cal = Calibration.from_arrays(
            doses=CALIBRATION_DOSES,
            red_pixels=KNOWN_RED.pixel(CALIBRATION_DOSES),
            green_pixels=KNOWN_GREEN.pixel(CALIBRATION_DOSES),
            blue_pixels=KNOWN_BLUE.pixel(CALIBRATION_DOSES),
        )

        red = KNOWN_RED.pixel(np.ones((2, 2)))
        film = FilmScan(red=red, green=red, blue=red)
        solver = MultigaussianSolver(mg_cal)
        result = solver.solve(film, cal.result)
        assert result.method == "multigaussian"

    def test_uncertainty_is_provided(self) -> None:
        mg_cal = _make_mg_calibration()
        from chromadose.calibration import Calibration
        cal = Calibration.from_arrays(
            doses=CALIBRATION_DOSES,
            red_pixels=KNOWN_RED.pixel(CALIBRATION_DOSES),
            green_pixels=KNOWN_GREEN.pixel(CALIBRATION_DOSES),
            blue_pixels=KNOWN_BLUE.pixel(CALIBRATION_DOSES),
        )

        dose_grid = np.full((2, 2), 2.0)
        film = FilmScan(
            red=KNOWN_RED.pixel(dose_grid),
            green=KNOWN_GREEN.pixel(dose_grid),
            blue=KNOWN_BLUE.pixel(dose_grid),
        )

        solver = MultigaussianSolver(mg_cal)
        result = solver.solve(film, cal.result)
        assert result.uncertainty.shape == (2, 2)
        assert np.all(result.uncertainty > 0)


def _make_mg_calibration_6ch(n_samples: int = 500) -> MultigaussianCalibration:
    """Create a 6-channel Multigaussian calibration (pre + post)."""
    rng = np.random.default_rng(42)
    doses = CALIBRATION_DOSES
    n_doses = len(doses)

    # Pre-irradiation values are dose-independent (unexposed film baseline)
    pre_r = float(KNOWN_RED.pixel(np.array([0.0]))[0])
    pre_g = float(KNOWN_GREEN.pixel(np.array([0.0]))[0])
    pre_b = float(KNOWN_BLUE.pixel(np.array([0.0]))[0])

    pixel_samples = np.zeros((n_doses, n_samples, 6))
    noise = 0.005
    for i, d in enumerate(doses):
        post_r = float(KNOWN_RED.pixel(np.array([d]))[0])
        post_g = float(KNOWN_GREEN.pixel(np.array([d]))[0])
        post_b = float(KNOWN_BLUE.pixel(np.array([d]))[0])

        mean = [pre_r, pre_g, pre_b, post_r, post_g, post_b]
        # 6x6 covariance: pre-channels correlated with each other,
        # post-channels correlated with each other, weak cross-correlation
        cov = np.eye(6) * noise**2
        cov[0:3, 0:3] += np.ones((3, 3)) * noise**2 * 0.3
        cov[3:6, 3:6] += np.ones((3, 3)) * noise**2 * 0.3
        np.fill_diagonal(cov, noise**2 * 1.5)

        pixel_samples[i] = rng.multivariate_normal(mean, cov, size=n_samples)

    return MultigaussianCalibration(doses=doses, pixel_samples=pixel_samples)


class TestMultigaussian6Channel:
    def test_6ch_calibration_construction(self) -> None:
        mg_cal = _make_mg_calibration_6ch()
        assert mg_cal.n_channels == 6
        assert mg_cal.means.shape == (7, 6)

    def test_6ch_solve(self) -> None:
        """6-channel solver should produce valid dose map."""
        mg_cal = _make_mg_calibration_6ch()
        from chromadose.calibration import Calibration
        cal = Calibration.from_arrays(
            doses=CALIBRATION_DOSES,
            red_pixels=KNOWN_RED.pixel(CALIBRATION_DOSES),
            green_pixels=KNOWN_GREEN.pixel(CALIBRATION_DOSES),
            blue_pixels=KNOWN_BLUE.pixel(CALIBRATION_DOSES),
        )

        dose_grid = np.array([[1.0, 3.0], [5.0, 7.0]])
        film = FilmScan(
            red=KNOWN_RED.pixel(dose_grid),
            green=KNOWN_GREEN.pixel(dose_grid),
            blue=KNOWN_BLUE.pixel(dose_grid),
        )
        # Pre-irradiation scan: dose=0 everywhere
        zero = np.zeros_like(dose_grid)
        pre_film = FilmScan(
            red=KNOWN_RED.pixel(zero),
            green=KNOWN_GREEN.pixel(zero),
            blue=KNOWN_BLUE.pixel(zero),
        )

        solver = MultigaussianSolver(mg_cal)
        result = solver.solve_6channel(film, pre_film, cal.result)

        assert result.method == "multigaussian-6ch"
        assert result.dose.shape == (2, 2)
        # Should be in the right ballpark
        np.testing.assert_allclose(result.dose, dose_grid, atol=1.0)

    def test_6ch_rejects_3ch_calibration(self) -> None:
        """solve_6channel should reject a 3-channel calibration."""
        mg_cal = _make_mg_calibration()  # 3-channel
        from chromadose.calibration import Calibration
        cal = Calibration.from_arrays(
            doses=CALIBRATION_DOSES,
            red_pixels=KNOWN_RED.pixel(CALIBRATION_DOSES),
            green_pixels=KNOWN_GREEN.pixel(CALIBRATION_DOSES),
            blue_pixels=KNOWN_BLUE.pixel(CALIBRATION_DOSES),
        )

        film = FilmScan(
            red=np.ones((2, 2)) * 0.1,
            green=np.ones((2, 2)) * 0.1,
            blue=np.ones((2, 2)) * 0.1,
        )

        solver = MultigaussianSolver(mg_cal)
        try:
            solver.solve_6channel(film, film, cal.result)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "6-channel" in str(e)
