"""Gamma analysis for comparing dose distributions.

Implements the gamma index formalism introduced by:
    Low DA, Harms WB, Mutic S, Purdy JA. "A technique for the quantitative
    evaluation of dose distributions." Medical Physics. 1998;25(5):656-61.

The gamma index γ at each point r_r in the reference distribution is:

    γ(r_r) = min{ Γ(r_r, r_e) } for all r_e in the evaluated distribution

    Γ(r_r, r_e) = sqrt( |r_r - r_e|² / ΔdM² + (D_r - D_e)² / ΔD² )

Where:
    ΔdM = distance-to-agreement criterion (mm)
    ΔD  = dose-difference criterion (% or Gy)
    r_r, r_e = spatial positions in reference/evaluated distributions
    D_r, D_e = dose values at those positions

This implementation uses the efficient geometric search approach: for each
reference point, search only within a spatial radius of ΔdM (since points
farther away can never have Γ < 1 from the distance term alone).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class GammaResult:
    """Result of a gamma analysis.

    Attributes:
        gamma_map: 2D gamma index at each reference point. Shape (H, W).
        pass_rate: Fraction of points with gamma <= 1.0 (within dose threshold).
        criteria: String description, e.g. "3%/3mm".
        dose_threshold_pct: Points below this % of max dose are excluded.
        points_evaluated: Number of points included in the analysis.
        points_passed: Number of points with gamma <= 1.0.
    """

    gamma_map: NDArray[np.floating]
    pass_rate: float
    criteria: str
    dose_threshold_pct: float
    points_evaluated: int
    points_passed: int
    metadata: dict = field(default_factory=dict)  # type: ignore[type-arg]


def gamma_2d(
    reference: NDArray[np.floating],
    evaluated: NDArray[np.floating],
    dose_criteria: float = 3.0,
    distance_criteria_mm: float = 3.0,
    pixel_size_mm: float = 1.0,
    dose_threshold_pct: float = 10.0,
    dose_criteria_is_global: bool = True,
    max_gamma: float = 2.0,
) -> GammaResult:
    """Compute 2D gamma index between two dose distributions.

    Parameters:
        reference: Reference dose distribution in Gy, shape (H, W).
        evaluated: Evaluated dose distribution in Gy, shape (H, W).
        dose_criteria: Dose difference criterion in percent.
        distance_criteria_mm: Distance-to-agreement criterion in mm.
        pixel_size_mm: Size of each pixel in mm (isotropic).
        dose_threshold_pct: Exclude points below this % of max reference dose.
        dose_criteria_is_global: If True, dose criterion is % of global max.
            If False, uses local (per-point) dose for the % calculation.
        max_gamma: Cap gamma values at this maximum (speeds computation).

    Returns:
        GammaResult with gamma map and pass rate.
    """
    if reference.shape != evaluated.shape:
        raise ValueError(
            f"Shape mismatch: reference {reference.shape} vs evaluated {evaluated.shape}"
        )

    H, W = reference.shape

    # Dose criterion in Gy
    if dose_criteria_is_global:
        dose_max = np.max(reference)
        dd_gy = dose_criteria / 100.0 * dose_max
    else:
        dd_gy = None  # computed per-point below

    # Search radius in pixels
    search_radius_px = int(np.ceil(distance_criteria_mm / pixel_size_mm))

    # Dose threshold mask
    dose_thresh = dose_threshold_pct / 100.0 * np.max(reference)
    mask = reference >= dose_thresh

    # Initialize gamma map
    gamma_map = np.full((H, W), max_gamma, dtype=np.float64)

    # Build coordinate offset grid for the search window
    offsets = np.arange(-search_radius_px, search_radius_px + 1)
    dy_grid, dx_grid = np.meshgrid(offsets, offsets, indexing="ij")
    dist_sq = (dy_grid * pixel_size_mm) ** 2 + (dx_grid * pixel_size_mm) ** 2
    # Mask to circular search region
    within_radius = dist_sq <= (distance_criteria_mm * max_gamma) ** 2

    # Vectorized: iterate over offsets, not pixels
    dta_sq = distance_criteria_mm ** 2

    for oy in range(len(offsets)):
        for ox in range(len(offsets)):
            if not within_radius[oy, ox]:
                continue

            dy = offsets[oy]
            dx = offsets[ox]
            r_sq = dist_sq[oy, ox]

            # Compute the overlap region
            # Reference region
            r_y0 = max(0, -dy)
            r_y1 = min(H, H - dy)
            r_x0 = max(0, -dx)
            r_x1 = min(W, W - dx)

            # Evaluated region (shifted)
            e_y0 = r_y0 + dy
            e_y1 = r_y1 + dy
            e_x0 = r_x0 + dx
            e_x1 = r_x1 + dx

            if r_y1 <= r_y0 or r_x1 <= r_x0:
                continue

            ref_slice = reference[r_y0:r_y1, r_x0:r_x1]
            eval_slice = evaluated[e_y0:e_y1, e_x0:e_x1]

            dose_diff = ref_slice - eval_slice

            if dd_gy is not None:
                # Global dose criterion
                dd_sq = dose_diff ** 2 / (dd_gy ** 2)
            else:
                # Local dose criterion
                local_dd = (dose_criteria / 100.0 * ref_slice) ** 2
                local_dd = np.where(local_dd > 1e-20, local_dd, 1e-20)
                dd_sq = dose_diff ** 2 / local_dd

            gamma_sq = r_sq / dta_sq + dd_sq
            gamma_val = np.sqrt(gamma_sq)

            # Update minimum gamma
            current = gamma_map[r_y0:r_y1, r_x0:r_x1]
            gamma_map[r_y0:r_y1, r_x0:r_x1] = np.minimum(current, gamma_val)

    # Apply threshold mask
    gamma_map = np.where(mask, gamma_map, np.nan)

    # Cap at max_gamma
    gamma_map = np.where(np.isnan(gamma_map), np.nan, np.minimum(gamma_map, max_gamma))

    # Statistics
    valid = gamma_map[~np.isnan(gamma_map)]
    points_evaluated = len(valid)
    points_passed = int(np.sum(valid <= 1.0))
    pass_rate = points_passed / points_evaluated if points_evaluated > 0 else 0.0

    criteria_str = f"{dose_criteria:.0f}%/{distance_criteria_mm:.0f}mm"
    if dose_criteria_is_global:
        criteria_str += " global"
    else:
        criteria_str += " local"

    return GammaResult(
        gamma_map=gamma_map,
        pass_rate=pass_rate,
        criteria=criteria_str,
        dose_threshold_pct=dose_threshold_pct,
        points_evaluated=points_evaluated,
        points_passed=points_passed,
        metadata={
            "dose_criteria_pct": dose_criteria,
            "distance_criteria_mm": distance_criteria_mm,
            "pixel_size_mm": pixel_size_mm,
        },
    )
