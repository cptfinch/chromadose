"""Shared fixtures and synthetic-data builders for the web API tests."""

from __future__ import annotations

import importlib.util
import io

import numpy as np
import pytest
import tifffile
from fastapi.testclient import TestClient

from app.main import create_app
from chromadose.core.types import FitParams

# Realistic EBT3 rational-function parameters: pixel(D) = (r + s*D) / (t + D).
_RED = FitParams(r=0.655, s=0.037, t=2.956)
_GREEN = FitParams(r=0.448, s=0.070, t=10.636)
_BLUE = FitParams(r=0.402, s=0.007, t=5.963)

HAS_PYDICOM = importlib.util.find_spec("pydicom") is not None


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def film_bytes(dose_grid: np.ndarray) -> bytes:
    """Encode a dose grid as a synthetic RGB float TIFF (bytes)."""
    rgb = np.stack(
        [_RED.pixel(dose_grid), _GREEN.pixel(dose_grid), _BLUE.pixel(dose_grid)], axis=-1
    ).astype(np.float32)
    buffer = io.BytesIO()
    tifffile.imwrite(buffer, rgb, photometric="rgb")
    return buffer.getvalue()


def uniform_film_bytes(dose: float, shape: tuple[int, int] = (16, 16)) -> bytes:
    return film_bytes(np.full(shape, float(dose)))


def npy_bytes(array: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(array, dtype=np.float64))
    return buffer.getvalue()


def rtplan_bytes(beams: list[dict]) -> bytes:
    """Build a minimal DICOM RT Plan (bytes) with the given beams."""
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    rt_plan_storage = "1.2.840.10008.5.1.4.1.1.481.5"
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = rt_plan_storage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta
    ds.SOPClassUID = rt_plan_storage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.Modality = "RTPLAN"
    ds.PatientName = "Test"
    ds.PatientID = "T1"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()

    beam_seq = []
    for b in beams:
        beam = Dataset()
        beam.BeamNumber = b["number"]
        beam.BeamName = b["name"]
        beam.TreatmentDeliveryType = b.get("delivery", "TREATMENT")
        cp = Dataset()
        cp.ControlPointIndex = 0
        cp.GantryAngle = b["gantry"]
        cp.BeamLimitingDeviceAngle = b["collimator"]
        cp.PatientSupportAngle = b["couch"]
        cp.NominalBeamEnergy = b.get("energy", 6.0)
        beam.ControlPointSequence = [cp]
        beam_seq.append(beam)
    ds.BeamSequence = beam_seq

    buffer = io.BytesIO()
    try:
        ds.save_as(buffer, enforce_file_format=True)
    except TypeError:
        ds.save_as(buffer, write_like_original=False)
    return buffer.getvalue()
