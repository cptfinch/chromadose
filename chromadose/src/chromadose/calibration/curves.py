"""Calibration curve fitting.

Fits the rational function model from Micke et al. (2011):
    pixel(D) = (r + s * D) / (t + D)

This is the same model used in the original Mathematica notebook
and in FilmQA Pro.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import curve_fit

from chromadose.core.types import FitParams


def rational_function(
    dose: NDArray[np.floating], r: float, s: float, t: float
) -> NDArray[np.floating]:
    """Micke et al. rational function: pixel = (r + s*D) / (t + D).

    Parameters:
        dose: Dose values in Gy.
        r, s, t: Fit parameters.

    Returns:
        Predicted pixel values.
    """
    return (r + s * dose) / (t + dose)


def fit_rational(
    doses: NDArray[np.floating],
    pixel_values: NDArray[np.floating],
) -> FitParams:
    """Fit the rational function to dose-pixel data for a single channel.

    Uses scipy.optimize.curve_fit (Levenberg-Marquardt) to find parameters
    (r, s, t) that minimize the sum of squared residuals between the model
    pixel(D) = (r + s*D) / (t + D) and the observed pixel values.

    This is the Python equivalent of Mathematica's FindFit used in the
    original gafchromic notebook.

    Parameters:
        doses: Known dose values in Gy, shape (n,).
        pixel_values: Mean pixel values at each dose, shape (n,).
            Must be normalized to [0, 1].

    Returns:
        FitParams with the optimized (r, s, t) values.

    Raises:
        RuntimeError: If the fit does not converge.
    """
    # Initial parameter estimates
    # r ≈ pixel at zero dose (unexposed film reflectance)
    # s ≈ pixel at very high dose (saturated film reflectance)
    # t ≈ 1.0 (scaling parameter)
    p0 = _initial_guess(doses, pixel_values)

    try:
        popt, _ = curve_fit(
            rational_function,
            doses,
            pixel_values,
            p0=p0,
            maxfev=5000,
        )
    except RuntimeError as e:
        raise RuntimeError(f"Calibration curve fit failed to converge: {e}") from e

    return FitParams(r=float(popt[0]), s=float(popt[1]), t=float(popt[2]))


def fit_all_channels(
    doses: NDArray[np.floating],
    pixel_values: NDArray[np.floating],
) -> tuple[FitParams, FitParams, FitParams]:
    """Fit calibration curves for all three RGB channels.

    Parameters:
        doses: Known dose values in Gy, shape (n,).
        pixel_values: Mean pixel values, shape (n, 3) for [R, G, B].

    Returns:
        Tuple of (red_params, green_params, blue_params).
    """
    red = fit_rational(doses, pixel_values[:, 0])
    green = fit_rational(doses, pixel_values[:, 1])
    blue = fit_rational(doses, pixel_values[:, 2])
    return red, green, blue


def _initial_guess(
    doses: NDArray[np.floating], pixel_values: NDArray[np.floating]
) -> tuple[float, float, float]:
    """Compute reasonable initial parameter estimates.

    For pixel(D) = (r + s*D) / (t + D):
    - At D=0: pixel(0) = r/t → r ≈ pixel(0) * t
    - At D→∞: pixel(∞) → s
    - t controls the transition steepness
    """
    sort_idx = np.argsort(doses)
    sorted_pixels = pixel_values[sort_idx]

    pixel_at_zero = sorted_pixels[0]  # unexposed
    pixel_at_max = sorted_pixels[-1]  # highest dose

    s = float(pixel_at_max) * 0.8  # asymptotic value
    t = 1.0
    r = float(pixel_at_zero) * t

    return (r, s, t)
