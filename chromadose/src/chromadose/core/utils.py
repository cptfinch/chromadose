"""Utility functions for chromadose."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def roi_mean(
    channel: NDArray[np.floating],
    x: int,
    y: int,
    width: int,
    height: int,
) -> float:
    """Extract the mean pixel value from a rectangular ROI.

    Parameters:
        channel: 2D array of pixel values (one color channel).
        x: Left edge of ROI (column index).
        y: Top edge of ROI (row index).
        width: Width of ROI in pixels.
        height: Height of ROI in pixels.

    Returns:
        Mean pixel value within the ROI.
    """
    roi = channel[y : y + height, x : x + width]
    return float(np.mean(roi))


def extract_roi_values(
    red: NDArray[np.floating],
    green: NDArray[np.floating],
    blue: NDArray[np.floating],
    rois: list[tuple[int, int, int, int]],
) -> NDArray[np.floating]:
    """Extract mean RGB values from a list of ROIs.

    Parameters:
        red: Red channel, shape (H, W).
        green: Green channel, shape (H, W).
        blue: Blue channel, shape (H, W).
        rois: List of (x, y, width, height) tuples defining rectangular ROIs.

    Returns:
        Array of shape (n_rois, 3) with mean [R, G, B] values per ROI.
    """
    values = np.zeros((len(rois), 3))
    for i, (x, y, w, h) in enumerate(rois):
        values[i, 0] = roi_mean(red, x, y, w, h)
        values[i, 1] = roi_mean(green, x, y, w, h)
        values[i, 2] = roi_mean(blue, x, y, w, h)
    return values
