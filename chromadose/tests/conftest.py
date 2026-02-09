"""Shared test fixtures for chromadose tests."""

import numpy as np
import pytest

from chromadose.core.types import CalibrationData, FitParams, CalibrationResult, FilmScan


# Realistic rational function parameters (typical EBT3 film)
# pixel(D) = (r + s*D) / (t + D)
KNOWN_RED = FitParams(r=0.655, s=0.037, t=2.956)
KNOWN_GREEN = FitParams(r=0.448, s=0.070, t=10.636)
KNOWN_BLUE = FitParams(r=0.402, s=0.007, t=5.963)

CALIBRATION_DOSES = np.array([0.0, 0.5, 1.0, 2.0, 4.0, 7.0, 9.0])


@pytest.fixture
def known_params() -> tuple[FitParams, FitParams, FitParams]:
    """Known fit parameters for testing."""
    return KNOWN_RED, KNOWN_GREEN, KNOWN_BLUE


@pytest.fixture
def synthetic_cal_data() -> CalibrationData:
    """Synthetic calibration data generated from known parameters.

    Pixel values are computed from the rational function with known params,
    so we can verify that fitting recovers the original parameters.
    """
    doses = CALIBRATION_DOSES
    red_pixels = KNOWN_RED.pixel(doses)
    green_pixels = KNOWN_GREEN.pixel(doses)
    blue_pixels = KNOWN_BLUE.pixel(doses)

    pixel_values = np.column_stack([red_pixels, green_pixels, blue_pixels])
    return CalibrationData(doses=doses, pixel_values=pixel_values)


@pytest.fixture
def synthetic_cal_result(synthetic_cal_data: CalibrationData) -> CalibrationResult:
    """Calibration result from synthetic data."""
    return CalibrationResult(
        red=KNOWN_RED, green=KNOWN_GREEN, blue=KNOWN_BLUE,
        cal_data=synthetic_cal_data,
    )


@pytest.fixture
def synthetic_film() -> FilmScan:
    """A small synthetic film scan with known doses at each pixel.

    Creates a 10x10 image where dose varies linearly from 0 to 5 Gy
    across columns, uniform across rows.
    """
    doses = np.linspace(0, 5, 10)
    # Create 10x10 images where each column has a known dose
    dose_grid = np.broadcast_to(doses, (10, 10))

    red = KNOWN_RED.pixel(dose_grid)
    green = KNOWN_GREEN.pixel(dose_grid)
    blue = KNOWN_BLUE.pixel(dose_grid)

    return FilmScan(red=red, green=green, blue=blue, dpi=72.0)
