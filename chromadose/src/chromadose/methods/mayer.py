"""Mayer et al. (2012) optimized multichannel dose solver.

Based on:
    Mayer RR, Ma F, Chen Y, et al. "Enhanced dosimetry procedures and
    assessment for EBT2 radiochromic film." Medical Physics. 2012;39(4):2147-55.
    DOI: 10.1118/1.3694100

This is the analytical solution to the multichannel problem. Instead of
numerically minimizing the residual (Micke), Mayer derives a closed-form
expression using the derivatives of the calibration curves.

Key equations (from the paper):
    D_opt = (D_ave - RS * Σ(D_k * A_k) / Σ(A_k)) / (1 - RS)     # eq. 6
    delta = Σ((D_opt - D_k) * A_k) / Σ(A_k²)                      # eq. 7
    RE = sqrt(Σ(D_k + A_k * delta - D_opt)²)                       # eq. 2
    RS = [Σ(A_k)]² / (3 * Σ(A_k²))                                 # eq. 9

Where:
    D_k = dose estimated from channel k alone (by inverting calibration curve)
    A_k = dD/d(pixel) for channel k (derivative of inverse calibration curve)
    delta = disturbance (non-dose perturbation, e.g. film thickness variation)
    RE = residual error (quality metric)
    RS = redundancy factor

This method is fully vectorized — no per-pixel loops.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from chromadose.core.types import CalibrationResult, DoseMap, FilmScan, FitParams


class MayerSolver:
    """Dose solver using the Mayer et al. (2012) analytical method.

    Faster than Micke (fully analytical, no iterative optimization),
    and provides quality metrics (disturbance map, residual error).
    """

    def solve(self, film: FilmScan, calibration: CalibrationResult) -> DoseMap:
        """Convert scanned film to dose using analytical multichannel optimization.

        Parameters:
            film: Scanned film with normalized RGB channels.
            calibration: Fitted calibration result.

        Returns:
            DoseMap with optimized dose, per-channel doses, and quality metrics.
        """
        d_min, d_max = calibration.dose_range

        # Per-channel dose and derivative (all vectorized over full image)
        Dr, Ar = _channel_dose_and_derivative(film.red, calibration.red)
        Dg, Ag = _channel_dose_and_derivative(film.green, calibration.green)
        Db, Ab = _channel_dose_and_derivative(film.blue, calibration.blue)

        # Clip to physical range
        Dr = np.clip(Dr, 0, d_max * 1.5)
        Dg = np.clip(Dg, 0, d_max * 1.5)
        Db = np.clip(Db, 0, d_max * 1.5)

        # Average dose
        D_ave = (Dr + Dg + Db) / 3.0

        # Mayer eq. 9: redundancy factor
        sum_Ak = Ar + Ag + Ab
        sum_Ak2 = Ar**2 + Ag**2 + Ab**2
        sum_DkAk = Dr * Ar + Dg * Ag + Db * Ab

        # Avoid division by zero
        sum_Ak2 = np.where(sum_Ak2 > 1e-20, sum_Ak2, 1e-20)
        RS = sum_Ak**2 / (sum_Ak2 * 3.0)

        # Mayer eq. 6: optimized dose
        denominator = np.where(np.abs(1.0 - RS) > 1e-10, 1.0 - RS, 1e-10)
        D_opt = (D_ave - RS * sum_DkAk / np.where(np.abs(sum_Ak) > 1e-20, sum_Ak, 1e-20)) / denominator

        # Clip to physical range
        D_opt = np.clip(D_opt, 0, d_max * 1.5)

        # Mayer eq. 7: disturbance map
        delta = (
            (D_opt - Dr) * Ar + (D_opt - Dg) * Ag + (D_opt - Db) * Ab
        ) / sum_Ak2

        # Mayer eq. 2: residual error
        RE = np.sqrt(
            (Dr + Ar * delta - D_opt) ** 2
            + (Dg + Ag * delta - D_opt) ** 2
            + (Db + Ab * delta - D_opt) ** 2
        )

        return DoseMap(
            dose=D_opt,
            uncertainty=RE,
            dose_r=Dr,
            dose_g=Dg,
            dose_b=Db,
            method="mayer",
            metadata={
                "disturbance": delta,
                "residual_error": RE,
                "redundancy_factor": RS,
            },
        )


def _channel_dose_and_derivative(
    pixels: NDArray[np.floating],
    params: FitParams,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Compute dose and dD/d(pixel) for a single channel.

    From pixel = (r + s*D) / (t + D), the inverse is:
        D = (r - pixel * t) / (pixel - s)

    The derivative dD/d(pixel) via implicit differentiation:
        d(pixel)/d(D) = (s*t - r) / (t + D)²
        dD/d(pixel) = (t + D)² / (s*t - r)

    We compute dD/d(pixel) directly from pixel values to avoid
    needing D first (which would be circular). Using the inverse:
        t + D = (r - s*t) / (pixel - s)    [from algebra]
        so dD/d(pixel) = (r - s*t) / (pixel - s)²  * (-1)
                       = -(r - s*t) / (pixel - s)²

    Wait — let's be more careful. From D = (r - pixel*t) / (pixel - s):
        dD/d(pixel) = [(-t)(pixel - s) - (r - pixel*t)(1)] / (pixel - s)²
                    = [-t*pixel + t*s - r + pixel*t] / (pixel - s)²
                    = (t*s - r) / (pixel - s)²
    """
    # Dose from inverse rational function
    denom = pixels - params.s
    # Avoid division by zero at pixels ≈ s (asymptotic value)
    safe_denom = np.where(np.abs(denom) > 1e-10, denom, np.sign(denom) * 1e-10)

    dose = (params.r - pixels * params.t) / safe_denom

    # Derivative dD/d(pixel)
    derivative = (params.t * params.s - params.r) / safe_denom**2

    return dose, np.abs(derivative)
