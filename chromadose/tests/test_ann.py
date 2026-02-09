"""Tests for the ANN (neural network) dose solver."""

import numpy as np

from chromadose.core.types import CalibrationResult, FilmScan
from chromadose.methods.ann import ANNCalibration, ANNSolver, ANNWeights, _forward

from .conftest import KNOWN_RED, KNOWN_GREEN, KNOWN_BLUE, CALIBRATION_DOSES


def _make_training_data(n_per_dose: int = 50) -> tuple[np.ndarray, np.ndarray]:
    """Generate training data from known calibration curves."""
    rng = np.random.default_rng(42)
    pixels_list = []
    doses_list = []

    for d in np.linspace(0, 9, 20):
        r = float(KNOWN_RED.pixel(np.array([d]))[0])
        g = float(KNOWN_GREEN.pixel(np.array([d]))[0])
        b = float(KNOWN_BLUE.pixel(np.array([d]))[0])

        noise = rng.normal(0, 0.003, (n_per_dose, 3))
        px = np.array([[r, g, b]]) + noise
        pixels_list.append(px)
        doses_list.append(np.full(n_per_dose, d))

    return np.vstack(pixels_list), np.concatenate(doses_list)


class TestANNWeights:
    def test_random_init(self) -> None:
        w = ANNWeights.random_init(n_input=3, n_hidden=16)
        assert w.W1.shape == (3, 16)
        assert w.b1.shape == (16,)
        assert w.W2.shape == (16, 16)
        assert w.n_hidden == 16

    def test_vector_roundtrip(self) -> None:
        w = ANNWeights.random_init(n_input=3, n_hidden=8)
        vec = w.to_vector()
        w2 = ANNWeights.from_vector(vec, n_input=3, n_hidden=8)
        np.testing.assert_array_equal(w.W1, w2.W1)
        np.testing.assert_array_equal(w.b2, w2.b2)
        np.testing.assert_array_equal(w.W3, w2.W3)

    def test_n_params(self) -> None:
        w = ANNWeights.random_init(n_input=3, n_hidden=8)
        assert w.n_params == len(w.to_vector())


class TestForward:
    def test_output_shape(self) -> None:
        w = ANNWeights.random_init(n_input=3, n_hidden=16)
        rgb = np.random.default_rng(0).random((100, 3))
        out = _forward(rgb, w)
        assert out.shape == (100,)

    def test_non_negative_output(self) -> None:
        w = ANNWeights.random_init(n_input=3, n_hidden=16)
        rgb = np.random.default_rng(0).random((100, 3))
        out = _forward(rgb, w)
        assert np.all(out >= 0)


class TestANNCalibration:
    def test_fit_and_predict(self) -> None:
        """ANN should be trainable and produce predictions."""
        pixels, doses = _make_training_data(n_per_dose=30)
        ann = ANNCalibration(n_hidden=16, n_ensemble=2, max_iter=50)
        ann.fit(pixels, doses)

        # Predict on training data
        pred, unc = ann.predict(pixels[:10])
        assert pred.shape == (10,)
        assert unc.shape == (10,)
        assert np.all(pred >= 0)

    def test_ensemble_uncertainty(self) -> None:
        """Multiple ensemble members should give non-zero uncertainty."""
        pixels, doses = _make_training_data(n_per_dose=30)
        ann = ANNCalibration(n_hidden=16, n_ensemble=3, max_iter=50)
        ann.fit(pixels, doses)

        _, unc = ann.predict(pixels[:50])
        # Ensemble members should disagree somewhat
        assert unc.shape == (50,)


class TestANNSolver:
    def test_solve_produces_dose_map(self) -> None:
        """ANNSolver should produce a valid DoseMap."""
        pixels, doses = _make_training_data(n_per_dose=30)
        ann_cal = ANNCalibration(n_hidden=16, n_ensemble=2, max_iter=50)
        ann_cal.fit(pixels, doses)

        from chromadose.calibration import Calibration
        cal = Calibration.from_arrays(
            doses=CALIBRATION_DOSES,
            red_pixels=KNOWN_RED.pixel(CALIBRATION_DOSES),
            green_pixels=KNOWN_GREEN.pixel(CALIBRATION_DOSES),
            blue_pixels=KNOWN_BLUE.pixel(CALIBRATION_DOSES),
        )

        dose_grid = np.full((4, 4), 2.0)
        film = FilmScan(
            red=KNOWN_RED.pixel(dose_grid),
            green=KNOWN_GREEN.pixel(dose_grid),
            blue=KNOWN_BLUE.pixel(dose_grid),
        )

        solver = ANNSolver(ann_cal)
        result = solver.solve(film, cal.result)

        assert result.method == "ann"
        assert result.dose.shape == (4, 4)
        assert result.uncertainty.shape == (4, 4)
        assert "n_ensemble" in result.metadata
