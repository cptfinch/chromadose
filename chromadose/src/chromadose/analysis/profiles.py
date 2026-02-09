"""Dose profile extraction and comparison.

Provides tools for extracting 1D dose profiles from 2D dose maps,
comparing measured profiles against TPS data, and computing metrics
like profile differences and distance-to-agreement (DTA).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d


@dataclass(frozen=True)
class DoseProfile:
    """A 1D dose profile.

    Attributes:
        position_mm: Position along the profile in mm, shape (N,).
        dose: Dose values in Gy at each position, shape (N,).
        label: Description (e.g. "Crossline at y=50mm").
    """

    position_mm: NDArray[np.floating]
    dose: NDArray[np.floating]
    label: str = ""

    @property
    def max_dose(self) -> float:
        return float(np.max(self.dose))

    @property
    def length_mm(self) -> float:
        return float(self.position_mm[-1] - self.position_mm[0])

    def interpolated(self, positions: NDArray[np.floating]) -> NDArray[np.floating]:
        """Interpolate the profile at the given positions."""
        f = interp1d(
            self.position_mm, self.dose,
            kind="linear", fill_value="extrapolate",
        )
        return f(positions)


def extract_row_profile(
    dose: NDArray[np.floating],
    row: int,
    pixel_size_mm: float = 1.0,
    label: str = "",
) -> DoseProfile:
    """Extract a horizontal (row) profile from a 2D dose map.

    Parameters:
        dose: 2D dose array, shape (H, W).
        row: Row index to extract.
        pixel_size_mm: Pixel size in mm.
        label: Optional label for the profile.

    Returns:
        DoseProfile along the specified row.
    """
    W = dose.shape[1]
    positions = np.arange(W, dtype=np.float64) * pixel_size_mm
    if not label:
        label = f"Row {row} (y={row * pixel_size_mm:.1f}mm)"
    return DoseProfile(position_mm=positions, dose=dose[row, :].copy(), label=label)


def extract_col_profile(
    dose: NDArray[np.floating],
    col: int,
    pixel_size_mm: float = 1.0,
    label: str = "",
) -> DoseProfile:
    """Extract a vertical (column) profile from a 2D dose map.

    Parameters:
        dose: 2D dose array, shape (H, W).
        col: Column index to extract.
        pixel_size_mm: Pixel size in mm.
        label: Optional label for the profile.

    Returns:
        DoseProfile along the specified column.
    """
    H = dose.shape[0]
    positions = np.arange(H, dtype=np.float64) * pixel_size_mm
    if not label:
        label = f"Col {col} (x={col * pixel_size_mm:.1f}mm)"
    return DoseProfile(position_mm=positions, dose=dose[:, col].copy(), label=label)


def extract_line_profile(
    dose: NDArray[np.floating],
    start: tuple[float, float],
    end: tuple[float, float],
    n_points: int = 200,
    pixel_size_mm: float = 1.0,
    label: str = "",
) -> DoseProfile:
    """Extract a profile along an arbitrary line through the dose map.

    Uses bilinear interpolation to sample dose values along the line.

    Parameters:
        dose: 2D dose array, shape (H, W).
        start: (row, col) start point in pixel coordinates.
        end: (row, col) end point in pixel coordinates.
        n_points: Number of sample points along the line.
        pixel_size_mm: Pixel size in mm.
        label: Optional label for the profile.

    Returns:
        DoseProfile along the line.
    """
    H, W = dose.shape
    t = np.linspace(0, 1, n_points)
    rows = start[0] + t * (end[0] - start[0])
    cols = start[1] + t * (end[1] - start[1])

    # Bilinear interpolation
    r0 = np.floor(rows).astype(int)
    c0 = np.floor(cols).astype(int)
    r1 = np.minimum(r0 + 1, H - 1)
    c1 = np.minimum(c0 + 1, W - 1)
    r0 = np.clip(r0, 0, H - 1)
    c0 = np.clip(c0, 0, W - 1)

    fr = rows - r0
    fc = cols - c0

    values = (
        dose[r0, c0] * (1 - fr) * (1 - fc)
        + dose[r1, c0] * fr * (1 - fc)
        + dose[r0, c1] * (1 - fr) * fc
        + dose[r1, c1] * fr * fc
    )

    # Distance along line in mm
    dr = (end[0] - start[0]) * pixel_size_mm
    dc = (end[1] - start[1]) * pixel_size_mm
    total_length = np.sqrt(dr ** 2 + dc ** 2)
    positions = t * total_length

    if not label:
        label = f"Line ({start[0]:.0f},{start[1]:.0f})->({end[0]:.0f},{end[1]:.0f})"

    return DoseProfile(position_mm=positions, dose=values, label=label)


@dataclass(frozen=True)
class ProfileComparison:
    """Result of comparing two dose profiles.

    Attributes:
        reference: The reference profile.
        evaluated: The evaluated profile (interpolated to reference positions).
        dose_diff: Dose difference (evaluated - reference) at each point.
        dose_diff_pct: Dose difference as % of reference max dose.
        mean_abs_diff_pct: Mean absolute dose difference in %.
        max_abs_diff_pct: Maximum absolute dose difference in %.
    """

    reference: DoseProfile
    evaluated: DoseProfile
    dose_diff: NDArray[np.floating]
    dose_diff_pct: NDArray[np.floating]
    mean_abs_diff_pct: float
    max_abs_diff_pct: float


def compare_profiles(
    reference: DoseProfile,
    evaluated: DoseProfile,
) -> ProfileComparison:
    """Compare two dose profiles by interpolating the evaluated profile
    onto the reference profile's positions.

    Parameters:
        reference: Reference dose profile (e.g. TPS).
        evaluated: Evaluated dose profile (e.g. film measurement).

    Returns:
        ProfileComparison with difference metrics.
    """
    # Interpolate evaluated onto reference positions
    eval_interp = evaluated.interpolated(reference.position_mm)

    dose_diff = eval_interp - reference.dose
    ref_max = reference.max_dose if reference.max_dose > 0 else 1.0
    dose_diff_pct = dose_diff / ref_max * 100.0

    return ProfileComparison(
        reference=reference,
        evaluated=DoseProfile(
            position_mm=reference.position_mm,
            dose=eval_interp,
            label=evaluated.label,
        ),
        dose_diff=dose_diff,
        dose_diff_pct=dose_diff_pct,
        mean_abs_diff_pct=float(np.mean(np.abs(dose_diff_pct))),
        max_abs_diff_pct=float(np.max(np.abs(dose_diff_pct))),
    )
