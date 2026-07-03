"""DICOM RT Dose file import and export.

Reads DICOM RT Dose files exported from treatment planning systems (TPS)
and converts them to numpy arrays for comparison with film measurements, and
writes measured film dose back out as an RT Dose file so it can be archived or
round-tripped into the TPS.

Requires the optional `pydicom` dependency:
    pip install chromadose[dicom]
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from chromadose.core.types import BeamGeometry

# DICOM SOP Class UID for RT Dose Storage.
_RT_DOSE_SOP_CLASS_UID = "1.2.840.10008.5.1.4.1.1.481.2"


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


def save_dicom_dose(
    dose: NDArray[np.floating],
    path: str | Path,
    pixel_spacing_mm: tuple[float, float] = (1.0, 1.0),
    origin_mm: tuple[float, float, float] = (0.0, 0.0, 0.0),
    slice_spacing_mm: float = 1.0,
    patient_name: str = "",
    patient_id: str = "",
    plan_label: str = "",
    dose_summation_type: str = "PLAN",
    geometry: BeamGeometry | None = None,
) -> None:
    """Write a dose distribution to a DICOM RT Dose file.

    Produces a minimal but valid RT Dose object (physical dose, units Gy) that
    round-trips through :func:`load_dicom_dose`. Dose is stored as unsigned
    32-bit integers with a ``DoseGridScaling`` factor, matching how treatment
    planning systems export RT Dose.

    Parameters:
        dose: Dose array in Gy. Either 2D (H, W) for a planar export or 3D
            (n_slices, H, W) for a volume.
        path: Output path for the DICOM file.
        pixel_spacing_mm: (row_spacing, col_spacing) in mm.
        origin_mm: (x, y, z) origin of the dose grid in mm (DICOM patient coords).
        slice_spacing_mm: Spacing between slices in mm (3D only).
        patient_name: Patient name for the DICOM header.
        patient_id: Patient ID for the DICOM header.
        plan_label: RT Plan label to record.
        dose_summation_type: DICOM DoseSummationType, e.g. "PLAN" or "BEAM".
        geometry: Optional IEC 61217 beam geometry to record. When given, the
            gantry / collimator / couch angles are written as standard DICOM
            angle attributes (a supplementary annotation — these belong to the
            RT Beam module, not the RT Dose IOD, but are widely readable).

    Raises:
        ImportError: If pydicom is not installed.
        ValueError: If the dose array is not 2D or 3D.
    """
    try:
        import pydicom
        from pydicom.dataset import Dataset, FileMetaDataset
        from pydicom.uid import UID, ExplicitVRLittleEndian, generate_uid
    except ImportError:
        raise ImportError(
            "pydicom is required for DICOM export. "
            "Install with: pip install chromadose[dicom]"
        )

    dose_arr = np.asarray(dose, dtype=np.float64)
    if dose_arr.ndim == 2:
        dose_arr = dose_arr[np.newaxis, :, :]
    elif dose_arr.ndim != 3:
        raise ValueError(f"dose must be 2D or 3D, got shape {dose.shape}")

    n_slices, rows, cols = dose_arr.shape

    # Clip non-physical negative dose to zero: film measurements can dip
    # slightly below zero from noise, and such values would wrap around to huge
    # numbers when cast to an unsigned integer.
    dose_arr = np.clip(dose_arr, 0.0, None)

    # Scale to uint32 with a DoseGridScaling factor (as TPS systems do). Store
    # as little-endian regardless of host byte order, to match the Explicit VR
    # Little Endian transfer syntax the file is written with.
    max_dose = float(dose_arr.max())
    uint32_max = np.iinfo(np.uint32).max
    dose_grid_scaling = max_dose / uint32_max if max_dose > 0 else 1.0
    pixel_data = np.round(dose_arr / dose_grid_scaling).astype("<u4")

    sop_class_uid = UID(_RT_DOSE_SOP_CLASS_UID)
    sop_instance_uid = generate_uid()

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = sop_class_uid
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta
    ds.SOPClassUID = sop_class_uid
    ds.SOPInstanceUID = sop_instance_uid

    # Patient / Study / Series
    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.FrameOfReferenceUID = generate_uid()
    ds.Modality = "RTDOSE"
    ds.Manufacturer = "chromadose"
    if plan_label:
        ds.RTPlanLabel = plan_label

    # IEC 61217 beam geometry (supplementary annotation)
    if geometry is not None:
        ds.GantryAngle = geometry.gantry_angle
        ds.BeamLimitingDeviceAngle = geometry.collimator_angle
        ds.PatientSupportAngle = geometry.couch_angle
        if geometry.beam_name:
            ds.BeamName = geometry.beam_name

    # Image geometry
    ds.ImagePositionPatient = [float(x) for x in origin_mm]
    ds.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    ds.PixelSpacing = [float(pixel_spacing_mm[0]), float(pixel_spacing_mm[1])]
    ds.SliceThickness = float(slice_spacing_mm)

    # Image Pixel module
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.Rows = rows
    ds.Columns = cols
    ds.BitsAllocated = 32
    ds.BitsStored = 32
    ds.HighBit = 31
    ds.PixelRepresentation = 0

    # RT Dose module
    ds.DoseUnits = "GY"
    ds.DoseType = "PHYSICAL"
    ds.DoseSummationType = dose_summation_type
    ds.DoseGridScaling = dose_grid_scaling
    if n_slices > 1:
        ds.NumberOfFrames = n_slices
        ds.FrameIncrementPointer = pydicom.tag.Tag(0x3004, 0x000C)  # GridFrameOffsetVector
        ds.GridFrameOffsetVector = [float(i * slice_spacing_mm) for i in range(n_slices)]

    ds.PixelData = pixel_data.tobytes()

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Encoding is taken from file_meta.TransferSyntaxUID. The keyword argument
    # that enforces a compliant file was renamed in pydicom 3.0
    # (write_like_original -> enforce_file_format), so support both.
    try:
        ds.save_as(str(out), enforce_file_format=True)
    except TypeError:
        ds.save_as(str(out), write_like_original=False)


def _dicom_value(dataset: Any, name: str) -> Any:
    """Return a DICOM element value, treating present-but-empty as absent.

    DICOM Type 2 elements can exist with an empty value (``None`` or ``""``);
    ``getattr(..., default)`` would return that empty value rather than the
    default, so normalize both to ``None``.
    """
    value = getattr(dataset, name, None)
    return None if value == "" else value


def _opt_float(dataset: Any, name: str) -> float | None:
    value = _dicom_value(dataset, name)
    return float(value) if value is not None else None


def _angle(dataset: Any, name: str) -> float:
    """Read an angle in degrees, defaulting to 0 and wrapping into [0, 360)."""
    value = _opt_float(dataset, name)
    return value % 360.0 if value is not None else 0.0


def load_beam_geometry(
    path: str | Path, include_setup: bool = False
) -> list[BeamGeometry]:
    """Read treatment beam geometry (IEC 61217) from a DICOM RT Plan file.

    Gantry, collimator (beam-limiting device) and couch (patient support) angles
    are taken from each beam's first control point. RT Plan angles are already
    in the IEC 61217 convention, so no conversion is applied (only wrapping into
    [0, 360)).

    Parameters:
        path: Path to a DICOM RT Plan file.
        include_setup: If True, include setup beams (TreatmentDeliveryType
            "SETUP"); by default only treatment beams are returned.

    Returns:
        One BeamGeometry per beam, in plan order.

    Raises:
        ImportError: If pydicom is not installed.
        ValueError: If the file has no BeamSequence (not an RT Plan).
    """
    try:
        import pydicom
    except ImportError:
        raise ImportError(
            "pydicom is required for DICOM import. "
            "Install with: pip install chromadose[dicom]"
        )

    ds = pydicom.dcmread(str(Path(path)))
    if not hasattr(ds, "BeamSequence"):
        raise ValueError(f"File has no BeamSequence (not an RT Plan?): {path}")

    beams: list[BeamGeometry] = []
    for beam in ds.BeamSequence:
        delivery = _dicom_value(beam, "TreatmentDeliveryType")
        if not include_setup and delivery == "SETUP":
            continue

        control_points = getattr(beam, "ControlPointSequence", None) or []
        cp0 = control_points[0] if control_points else None

        number = _dicom_value(beam, "BeamNumber")
        name = _dicom_value(beam, "BeamName")

        beams.append(
            BeamGeometry(
                gantry_angle=_angle(cp0, "GantryAngle") if cp0 is not None else 0.0,
                collimator_angle=_angle(cp0, "BeamLimitingDeviceAngle") if cp0 is not None else 0.0,
                couch_angle=_angle(cp0, "PatientSupportAngle") if cp0 is not None else 0.0,
                beam_name=str(name) if name is not None else "",
                beam_number=int(number) if number is not None else None,
                beam_energy_mv=_opt_float(cp0, "NominalBeamEnergy") if cp0 is not None else None,
                ssd_mm=_opt_float(cp0, "SourceToSurfaceDistance") if cp0 is not None else None,
            )
        )
    return beams


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
