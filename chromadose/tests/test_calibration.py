"""Tests for calibration curve fitting."""

import json
import tempfile
from pathlib import Path

import numpy as np

from chromadose.calibration import Calibration
from chromadose.calibration.curves import fit_rational, rational_function
from chromadose.core.types import CalibrationData, FitParams

from .conftest import KNOWN_RED, KNOWN_GREEN, KNOWN_BLUE, CALIBRATION_DOSES


class TestRationalFunction:
    def test_model_shape(self) -> None:
        doses = np.array([0, 1, 2, 3])
        result = rational_function(doses, r=0.6, s=0.04, t=3.0)
        assert result.shape == (4,)

    def test_known_values(self) -> None:
        # pixel(0) = r/t = 0.6/3.0 = 0.2
        result = rational_function(np.array([0.0]), r=0.6, s=0.04, t=3.0)
        np.testing.assert_allclose(result, 0.2, rtol=1e-10)


class TestFitRational:
    def test_recovers_known_params(self) -> None:
        """Fitting noiseless data should recover the original parameters."""
        doses = CALIBRATION_DOSES
        pixels = KNOWN_RED.pixel(doses)

        fitted = fit_rational(doses, pixels)

        np.testing.assert_allclose(fitted.r, KNOWN_RED.r, rtol=1e-3)
        np.testing.assert_allclose(fitted.s, KNOWN_RED.s, rtol=1e-3)
        np.testing.assert_allclose(fitted.t, KNOWN_RED.t, rtol=1e-3)

    def test_fit_with_noise(self) -> None:
        """Fitting noisy data should still get close."""
        rng = np.random.default_rng(42)
        doses = CALIBRATION_DOSES
        pixels = KNOWN_RED.pixel(doses) + rng.normal(0, 0.002, size=len(doses))

        fitted = fit_rational(doses, pixels)

        # With small noise, should be within 10%
        # (s is the asymptotic value at high dose — small absolute value,
        # so relative tolerance needs to be more generous)
        np.testing.assert_allclose(fitted.r, KNOWN_RED.r, rtol=0.10)
        np.testing.assert_allclose(fitted.s, KNOWN_RED.s, rtol=0.10)
        np.testing.assert_allclose(fitted.t, KNOWN_RED.t, rtol=0.10)


class TestCalibration:
    def test_from_arrays(self) -> None:
        doses = CALIBRATION_DOSES
        cal = Calibration.from_arrays(
            doses=doses,
            red_pixels=KNOWN_RED.pixel(doses),
            green_pixels=KNOWN_GREEN.pixel(doses),
            blue_pixels=KNOWN_BLUE.pixel(doses),
        )
        # Should recover params for all channels
        np.testing.assert_allclose(cal.result.red.r, KNOWN_RED.r, rtol=1e-3)
        np.testing.assert_allclose(cal.result.green.r, KNOWN_GREEN.r, rtol=1e-3)
        np.testing.assert_allclose(cal.result.blue.r, KNOWN_BLUE.r, rtol=1e-3)

    def test_save_load_roundtrip(self) -> None:
        doses = CALIBRATION_DOSES
        cal = Calibration.from_arrays(
            doses=doses,
            red_pixels=KNOWN_RED.pixel(doses),
            green_pixels=KNOWN_GREEN.pixel(doses),
            blue_pixels=KNOWN_BLUE.pixel(doses),
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            cal.save(f.name)
            loaded = Calibration.load(f.name)

        np.testing.assert_allclose(loaded.result.red.r, cal.result.red.r, rtol=1e-10)
        np.testing.assert_allclose(loaded.result.green.s, cal.result.green.s, rtol=1e-10)
        np.testing.assert_allclose(loaded.result.blue.t, cal.result.blue.t, rtol=1e-10)

    def test_summary(self) -> None:
        doses = CALIBRATION_DOSES
        cal = Calibration.from_arrays(
            doses=doses,
            red_pixels=KNOWN_RED.pixel(doses),
            green_pixels=KNOWN_GREEN.pixel(doses),
            blue_pixels=KNOWN_BLUE.pixel(doses),
        )
        summary = cal.summary()
        assert "Dose range: 0.00 - 9.00 Gy" in summary
        assert "Red:" in summary
