"""Tests for core data types."""

import numpy as np
import pytest

from chromadose.core.types import CalibrationData, FitParams, FilmScan


class TestFitParams:
    """Tests for the rational function model."""

    def test_pixel_at_zero_dose(self) -> None:
        p = FitParams(r=0.655, s=0.037, t=2.956)
        result = p.pixel(np.array([0.0]))
        expected = 0.655 / 2.956
        np.testing.assert_allclose(result, expected, rtol=1e-10)

    def test_pixel_decreases_with_dose(self) -> None:
        p = FitParams(r=0.655, s=0.037, t=2.956)
        doses = np.array([0.0, 1.0, 5.0, 10.0])
        pixels = p.pixel(doses)
        # For radiochromic film, pixel value decreases with dose
        assert np.all(np.diff(pixels) < 0)

    def test_dose_inverts_pixel(self) -> None:
        """dose(pixel(D)) should recover D."""
        p = FitParams(r=0.655, s=0.037, t=2.956)
        doses = np.array([0.5, 1.0, 2.0, 5.0])
        pixels = p.pixel(doses)
        recovered = p.dose(pixels)
        np.testing.assert_allclose(recovered, doses, rtol=1e-10)

    def test_derivative_sign(self) -> None:
        """Derivative should be negative (pixel decreases with dose)."""
        p = FitParams(r=0.655, s=0.037, t=2.956)
        doses = np.array([0.0, 1.0, 5.0])
        deriv = p.dpixel_ddose(doses)
        assert np.all(deriv < 0)


class TestCalibrationData:
    def test_shape_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="doses has 3 entries"):
            CalibrationData(
                doses=np.array([0, 1, 2]),
                pixel_values=np.ones((4, 3)),
            )

    def test_wrong_channels_raises(self) -> None:
        with pytest.raises(ValueError, match="must be"):
            CalibrationData(
                doses=np.array([0, 1, 2]),
                pixel_values=np.ones((3, 4)),
            )

    def test_valid_construction(self, synthetic_cal_data: CalibrationData) -> None:
        assert synthetic_cal_data.n_doses == 7
        assert synthetic_cal_data.channels == 3


class TestFilmScan:
    def test_shape(self) -> None:
        red = np.ones((100, 200))
        scan = FilmScan(red=red, green=red, blue=red, dpi=150)
        assert scan.shape == (100, 200)

    def test_rgb_stacking(self) -> None:
        r = np.ones((10, 10)) * 0.5
        g = np.ones((10, 10)) * 0.3
        b = np.ones((10, 10)) * 0.2
        scan = FilmScan(red=r, green=g, blue=b)
        assert scan.rgb.shape == (10, 10, 3)
        np.testing.assert_allclose(scan.rgb[0, 0], [0.5, 0.3, 0.2])

    def test_pixel_size(self) -> None:
        scan = FilmScan(
            red=np.ones((10, 10)),
            green=np.ones((10, 10)),
            blue=np.ones((10, 10)),
            dpi=254,
        )
        np.testing.assert_allclose(scan.pixel_size_mm, 0.1, rtol=1e-3)
