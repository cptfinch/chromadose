"""Film-to-TPS dose registration (spatial alignment).

When comparing a film measurement to a TPS dose distribution, the two
must be spatially aligned. This module provides:

1. Manual registration: specify known landmark positions
2. Automatic registration: optimize translation/rotation to minimize
   dose difference or maximize gamma pass rate

The registration model supports rigid transformations (translation + rotation).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import map_coordinates
from scipy.optimize import minimize


@dataclass(frozen=True)
class RegistrationResult:
    """Result of a spatial registration.

    Attributes:
        dx_mm: Translation in x (columns) in mm.
        dy_mm: Translation in y (rows) in mm.
        angle_deg: Rotation angle in degrees (counter-clockwise).
        registered: The registered (transformed) evaluated dose map.
        cost: Final cost function value.
    """

    dx_mm: float
    dy_mm: float
    angle_deg: float
    registered: NDArray[np.floating]
    cost: float


def apply_rigid_transform(
    image: NDArray[np.floating],
    dx_px: float,
    dy_px: float,
    angle_deg: float,
) -> NDArray[np.floating]:
    """Apply a rigid transformation (translation + rotation) to a 2D image.

    Rotation is about the image center, followed by translation.
    Uses bilinear interpolation via scipy.ndimage.map_coordinates.

    Parameters:
        image: 2D array, shape (H, W).
        dx_px: Translation in x (columns) in pixels.
        dy_px: Translation in y (rows) in pixels.
        angle_deg: Rotation in degrees (counter-clockwise).

    Returns:
        Transformed image, same shape, with zeros at out-of-bounds regions.
    """
    H, W = image.shape
    cy, cx = H / 2.0, W / 2.0

    # Build output coordinate grid
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

    # Center, rotate, uncenter, then translate
    angle_rad = np.deg2rad(-angle_deg)  # inverse mapping
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)

    # Inverse transform: for each output pixel, find the input pixel
    yc = yy - cy - dy_px
    xc = xx - cx - dx_px

    src_y = cos_a * yc - sin_a * xc + cy
    src_x = sin_a * yc + cos_a * xc + cx

    return map_coordinates(image, [src_y, src_x], order=1, mode="constant", cval=0.0)


def register_auto(
    reference: NDArray[np.floating],
    evaluated: NDArray[np.floating],
    pixel_size_mm: float = 1.0,
    max_shift_mm: float = 10.0,
    max_angle_deg: float = 5.0,
    dose_threshold_pct: float = 10.0,
) -> RegistrationResult:
    """Automatically register evaluated dose to reference by minimizing
    the sum of squared dose differences.

    Parameters:
        reference: Reference dose (e.g. TPS), shape (H, W).
        evaluated: Evaluated dose (e.g. film), shape (H, W).
        pixel_size_mm: Pixel size in mm.
        max_shift_mm: Maximum allowed translation in mm.
        max_angle_deg: Maximum allowed rotation in degrees.
        dose_threshold_pct: Exclude points below this % of max dose.

    Returns:
        RegistrationResult with optimal transformation and registered image.
    """
    if reference.shape != evaluated.shape:
        raise ValueError(
            f"Shape mismatch: reference {reference.shape} vs evaluated {evaluated.shape}"
        )

    max_shift_px = max_shift_mm / pixel_size_mm
    thresh = dose_threshold_pct / 100.0 * np.max(reference)
    mask = reference >= thresh

    def cost(params: NDArray) -> float:
        dx_px, dy_px, angle = params
        transformed = apply_rigid_transform(evaluated, dx_px, dy_px, angle)
        diff = (reference - transformed)[mask]
        return float(np.mean(diff ** 2))

    # Optimize
    result = minimize(
        cost,
        x0=[0.0, 0.0, 0.0],
        method="L-BFGS-B",
        bounds=[
            (-max_shift_px, max_shift_px),
            (-max_shift_px, max_shift_px),
            (-max_angle_deg, max_angle_deg),
        ],
    )

    dx_px, dy_px, angle_deg = result.x
    registered = apply_rigid_transform(evaluated, dx_px, dy_px, angle_deg)

    return RegistrationResult(
        dx_mm=dx_px * pixel_size_mm,
        dy_mm=dy_px * pixel_size_mm,
        angle_deg=angle_deg,
        registered=registered,
        cost=result.fun,
    )


def register_manual(
    evaluated: NDArray[np.floating],
    dx_mm: float,
    dy_mm: float,
    angle_deg: float = 0.0,
    pixel_size_mm: float = 1.0,
) -> RegistrationResult:
    """Apply a manual rigid registration to the evaluated dose map.

    Parameters:
        evaluated: Evaluated dose, shape (H, W).
        dx_mm: Translation in x (mm).
        dy_mm: Translation in y (mm).
        angle_deg: Rotation angle in degrees.
        pixel_size_mm: Pixel size in mm.

    Returns:
        RegistrationResult with the transformed image.
    """
    dx_px = dx_mm / pixel_size_mm
    dy_px = dy_mm / pixel_size_mm
    registered = apply_rigid_transform(evaluated, dx_px, dy_px, angle_deg)

    return RegistrationResult(
        dx_mm=dx_mm,
        dy_mm=dy_mm,
        angle_deg=angle_deg,
        registered=registered,
        cost=0.0,
    )
