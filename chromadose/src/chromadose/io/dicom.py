"""DICOM RT Dose file import.

Reads DICOM RT Dose files exported from treatment planning systems (TPS)
and converts them to numpy arrays for comparison with film measurements.

Requires the optional `pydicom` dependency:
    pip install chromadose[dicom]
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class RTDose:
    """A dose distribution loaded from a DICOM RT Dose file.

    Attributes:
        dose: 3D dose array in Gy, shape (n_slices, H, W).
            For planar exports, n_slices = 1.
        pixel_spacing_mm: (row_spacing, col_spacing) in mm.
        origin_mm: (x, y, z) origin of the dose grid in mm (DICOM patient coords).
        patient_name: Patient name from DICOM header.
        plan_label: RT Plan label, if available.
    """

    dose: NDArray[np.floating]
    pixel_spacing_mm: tuple[float, float]
    origin_mm: tuple[float, float, float]
    patient_name: str = ""
    plan_label: str = ""

    @property
    def shape(self) -> tuple[int, ...]:
        return self.dose.shape

    @property
    def n_slices(self) -> int:
        return self.dose.shape[0]

    def slice_2d(self, index: int = 0) -> NDArray[np.floating]:
        """Extract a single 2D slice from the dose volume."""
        return self.dose[index]

    def max_dose_slice(self) -> tuple[int, NDArray[np.floating]]:
        """Return the slice containing the maximum dose."""
        max_per_slice = np.array([np.max(self.dose[i]) for i in range(self.n_slices)])
        idx = int(np.argmax(max_per_slice))
        return idx, self.dose[idx]


def load_dicom_dose(path: str | Path) -> RTDose:
    """Load a DICOM RT Dose file and return an RTDose object.

    Parameters:
        path: Path to the DICOM RT Dose file.

    Returns:
        RTDose with dose in Gy.

    Raises:
        ImportError: If pydicom is not installed.
        ValueError: If the file is not a valid RT Dose file.
    """
    try:
        import pydicom
    except ImportError:
        raise ImportError(
            "pydicom is required for DICOM import. "
            "Install with: pip install chromadose[dicom]"
        )

    path = Path(path)
    ds = pydicom.dcmread(str(path))

    # Verify this is an RT Dose file
    if not hasattr(ds, "DoseGridScaling"):
        raise ValueError(f"File does not appear to be an RT Dose file: {path}")

    # Extract dose array and scale to Gy
    dose_grid_scaling = float(ds.DoseGridScaling)
    pixel_data = ds.pixel_array.astype(np.float64)
    dose_gy = pixel_data * dose_grid_scaling

    # Ensure 3D: (slices, rows, cols)
    if dose_gy.ndim == 2:
        dose_gy = dose_gy[np.newaxis, :, :]

    # Pixel spacing
    if hasattr(ds, "PixelSpacing"):
        row_spacing = float(ds.PixelSpacing[0])
        col_spacing = float(ds.PixelSpacing[1])
    else:
        row_spacing = 1.0
        col_spacing = 1.0

    # Origin
    if hasattr(ds, "ImagePositionPatient"):
        origin = tuple(float(x) for x in ds.ImagePositionPatient)
    else:
        origin = (0.0, 0.0, 0.0)

    # Patient info
    patient_name = str(getattr(ds, "PatientName", ""))
    plan_label = str(getattr(ds, "RTPlanLabel", ""))

    return RTDose(
        dose=dose_gy,
        pixel_spacing_mm=(row_spacing, col_spacing),
        origin_mm=origin,  # type: ignore[arg-type]
        patient_name=patient_name,
        plan_label=plan_label,
    )


def resample_to_film(
    rt_dose: RTDose,
    film_shape: tuple[int, int],
    film_pixel_size_mm: float,
    slice_index: int = 0,
) -> NDArray[np.floating]:
    """Resample an RT Dose slice to match a film's pixel grid.

    Uses bilinear interpolation to resample the TPS dose grid onto the
    film measurement grid. Assumes the dose and film are already aligned
    (centered on each other).

    Parameters:
        rt_dose: The RT Dose object.
        film_shape: (H, W) of the film in pixels.
        film_pixel_size_mm: Film pixel size in mm.
        slice_index: Which slice of the dose volume to use.

    Returns:
        2D dose array resampled to the film grid, shape (H, W).
    """
    from scipy.interpolate import RegularGridInterpolator

    dose_2d = rt_dose.slice_2d(slice_index)
    dH, dW = dose_2d.shape
    row_sp, col_sp = rt_dose.pixel_spacing_mm

    # Build coordinate axes for the dose grid (centered)
    dose_rows = np.arange(dH) * row_sp
    dose_cols = np.arange(dW) * col_sp
    dose_rows -= dose_rows.mean()
    dose_cols -= dose_cols.mean()

    # Build coordinate axes for the film grid (centered)
    fH, fW = film_shape
    film_rows = np.arange(fH) * film_pixel_size_mm
    film_cols = np.arange(fW) * film_pixel_size_mm
    film_rows -= film_rows.mean()
    film_cols -= film_cols.mean()

    # Interpolate
    interp = RegularGridInterpolator(
        (dose_rows, dose_cols), dose_2d,
        method="linear", bounds_error=False, fill_value=0.0,
    )

    film_row_grid, film_col_grid = np.meshgrid(film_rows, film_cols, indexing="ij")
    points = np.column_stack([film_row_grid.ravel(), film_col_grid.ravel()])

    resampled = interp(points).reshape(fH, fW)
    return resampled
