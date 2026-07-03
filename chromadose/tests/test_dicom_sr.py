"""Tests for the DICOM Structured Report (SR) export.

These tests require pydicom and are skipped when it is unavailable.
"""

import importlib.util
from datetime import datetime

import numpy as np
import pytest

from chromadose.analysis.gamma import gamma_2d
from chromadose.io.dicom_sr import read_dicom_sr, save_dicom_sr

_HAS_PYDICOM = importlib.util.find_spec("pydicom") is not None
pytestmark = pytest.mark.skipif(not _HAS_PYDICOM, reason="pydicom not installed")


def _gamma_result():  # type: ignore[no-untyped-def]
    ref = np.ones((20, 20)) * 2.0
    meas = ref + 0.01
    return gamma_2d(ref, meas, dose_criteria=3.0, distance_criteria_mm=3.0)


class TestSaveDicomSR:
    def test_full_report_roundtrip(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """A full SR should round-trip method, gamma metrics and dose stats."""
        gamma = _gamma_result()
        out = tmp_path / "qa.dcm"

        save_dicom_sr(
            out,
            gamma_result=gamma,
            max_dose_gy=2.5,
            mean_dose_gy=2.01,
            method="micke",
            film_type="EBT3",
            patient_name="QA Phantom",
            patient_id="QA001",
            plan_label="VMAT",
            content_datetime=datetime(2026, 6, 30, 12, 0, 0),
        )

        values = read_dicom_sr(out)
        assert values["Dosimetry method"] == "micke"
        assert values["Film type"] == "EBT3"
        assert values["RT Plan label"] == "VMAT"
        assert values["Gamma criteria"] == gamma.criteria
        assert values["Gamma pass rate"] == pytest.approx(gamma.pass_rate * 100.0, abs=1e-3)
        assert values["Points evaluated"] == pytest.approx(float(gamma.points_evaluated))
        assert values["Points passed"] == pytest.approx(float(gamma.points_passed))
        assert values["Dose threshold"] == pytest.approx(gamma.dose_threshold_pct)
        assert values["Maximum dose"] == pytest.approx(2.5)
        assert values["Mean dose"] == pytest.approx(2.01)

    def test_is_valid_sr_document(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """The written file should be a Comprehensive SR with a CONTAINER root."""
        import pydicom

        out = tmp_path / "qa.dcm"
        save_dicom_sr(out, max_dose_gy=3.0, mean_dose_gy=1.0)

        ds = pydicom.dcmread(str(out))
        assert ds.Modality == "SR"
        assert ds.SOPClassUID == "1.2.840.10008.5.1.4.1.1.88.33"
        assert ds.ValueType == "CONTAINER"
        assert ds.CompletionFlag == "COMPLETE"

    def test_gamma_only(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """An SR with only a gamma result omits the dose-statistics section."""
        out = tmp_path / "qa.dcm"
        save_dicom_sr(out, gamma_result=_gamma_result())

        values = read_dicom_sr(out)
        assert "Gamma pass rate" in values
        assert "Maximum dose" not in values

    def test_minimal_report(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """A report with no sections is still a valid, readable SR."""
        out = tmp_path / "empty.dcm"
        save_dicom_sr(out)
        assert read_dicom_sr(out) == {}

    def test_beam_geometry_recorded(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """IEC 61217 beam geometry round-trips into the SR content tree."""
        from chromadose.core.types import BeamGeometry

        out = tmp_path / "qa.dcm"
        save_dicom_sr(
            out,
            geometry=BeamGeometry(gantry_angle=90.0, collimator_angle=45.0,
                                  couch_angle=15.0, beam_name="LLAT", beam_energy_mv=6.0),
        )
        values = read_dicom_sr(out)
        assert values["Beam name"] == "LLAT"
        assert values["Gantry angle"] == pytest.approx(90.0)
        assert values["Collimator angle"] == pytest.approx(45.0)
        assert values["Couch angle"] == pytest.approx(15.0)
        assert values["Beam energy"] == pytest.approx(6.0)

    def test_explicit_study_series_uid(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """Provided study/series UIDs are used so the SR can join an existing study."""
        import pydicom

        out = tmp_path / "qa.dcm"
        save_dicom_sr(
            out,
            max_dose_gy=1.0,
            study_instance_uid="1.2.3.4.5",
            series_instance_uid="1.2.3.4.6",
        )
        ds = pydicom.dcmread(str(out))
        assert ds.StudyInstanceUID == "1.2.3.4.5"
        assert ds.SeriesInstanceUID == "1.2.3.4.6"
        # Type 2 attributes required by PACS must be present.
        for attr in ("PatientName", "PatientID", "ReferringPhysicianName", "StudyID", "AccessionNumber"):
            assert attr in ds
        assert ds.SpecificCharacterSet == "ISO_IR 192"
