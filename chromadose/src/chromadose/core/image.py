"""TIFF image loading and RGB channel separation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile
from numpy.typing import NDArray

from chromadose.core.types import FilmScan

# 16-bit max value for normalization
_UINT16_MAX = 65535.0


def load_tiff(path: str | Path) -> FilmScan:
    """Load a scanned TIFF image and return a FilmScan with normalized RGB channels.

    Handles 8-bit, 16-bit, and float TIFF images. Pixel values are normalized
    to [0, 1] range.

    Parameters:
        path: Path to a TIFF file (RGB, scanned film).

    Returns:
        FilmScan with separated R, G, B channels and DPI metadata.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"TIFF file not found: {path}")

    with tifffile.TiffFile(path) as tif:
        data = tif.asarray()
        # Extract DPI from TIFF tags if available
        dpi = _extract_dpi(tif)

    return _array_to_film_scan(data, dpi)


def load_tiff_averaged(paths: list[str | Path]) -> FilmScan:
    """Load multiple TIFF scans and average them to reduce noise.

    All images must have the same dimensions.

    Parameters:
        paths: List of paths to TIFF files of the same film.

    Returns:
        FilmScan with averaged RGB channels.
    """
    if not paths:
        raise ValueError("At least one path is required")

    scans = [load_tiff(p) for p in paths]

    # Verify all same shape
    shapes = {s.shape for s in scans}
    if len(shapes) > 1:
        raise ValueError(f"All scans must have the same dimensions, got: {shapes}")

    red = np.mean([s.red for s in scans], axis=0)
    green = np.mean([s.green for s in scans], axis=0)
    blue = np.mean([s.blue for s in scans], axis=0)

    return FilmScan(red=red, green=green, blue=blue, dpi=scans[0].dpi)


def _array_to_film_scan(data: NDArray, dpi: float) -> FilmScan:  # type: ignore[type-arg]
    """Convert a raw numpy array from TIFF to a FilmScan."""
    if data.ndim == 2:
        # Grayscale — treat as single channel replicated
        normalized = _normalize(data)
        return FilmScan(red=normalized, green=normalized, blue=normalized, dpi=dpi)

    if data.ndim == 3:
        n_channels = data.shape[2] if data.shape[2] <= 4 else data.shape[0]

        if data.shape[2] <= 4:
            # (H, W, C) layout — standard
            red = _normalize(data[:, :, 0])
            green = _normalize(data[:, :, 1])
            blue = _normalize(data[:, :, 2])
        else:
            # (C, H, W) layout — some scanners
            red = _normalize(data[0, :, :])
            green = _normalize(data[1, :, :])
            blue = _normalize(data[2, :, :])

        return FilmScan(red=red, green=green, blue=blue, dpi=dpi)

    raise ValueError(f"Unexpected TIFF array shape: {data.shape}")


def _normalize(channel: NDArray) -> NDArray[np.floating]:  # type: ignore[type-arg]
    """Normalize pixel values to [0, 1]."""
    if channel.dtype == np.uint16:
        return channel.astype(np.float64) / _UINT16_MAX
    elif channel.dtype == np.uint8:
        return channel.astype(np.float64) / 255.0
    elif np.issubdtype(channel.dtype, np.floating):
        if channel.max() > 1.0:
            return channel / _UINT16_MAX
        return channel.astype(np.float64)
    else:
        return channel.astype(np.float64) / _UINT16_MAX


def _extract_dpi(tif: tifffile.TiffFile) -> float:
    """Extract DPI from TIFF metadata. Defaults to 72 if not found."""
    try:
        page = tif.pages[0]
        tags = page.tags
        # Check for XResolution tag (tag 282)
        if "XResolution" in tags:
            res = tags["XResolution"].value
            if isinstance(res, tuple) and len(res) == 2:
                return float(res[0]) / float(res[1])
            return float(res)
    except (AttributeError, KeyError, TypeError, ZeroDivisionError):
        pass
    return 72.0
