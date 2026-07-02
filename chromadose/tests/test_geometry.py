"""Tests for IEC 61217 beam geometry: the BeamGeometry type and RT Plan reader.

The BeamGeometry validation tests need no DICOM. The RT Plan reader tests build
a synthetic plan with pydicom and are skipped when pydicom is unavailable.
"""

import importlib.util

import pytest

from chromadose.core.types import BeamGeometry
from chromadose.io.dicom import load_beam_geometry

_HAS_PYDICOM = importlib.util.find_spec("pydicom") is not None
requires_pydicom = pytest.mark.skipif(not _HAS_PYDICOM, reason="pydicom not installed")


class TestBeamGeometry:
    def test_defaults(self) -> None:
        g = BeamGeometry()
        assert g.gantry_angle == 0.0
        assert g.beam_number is None

    def test_valid_angles(self) -> None:
        g = BeamGeometry(gantry_angle=180.0, collimator_angle=90.0, couch_angle=350.0)
        assert g.couch_angle == 350.0

    @pytest.mark.parametrize("angle", [-1.0, 360.0, 400.0, float("nan")])
    def test_out_of_range_angle_raises(self, angle: float) -> None:
        with pytest.raises(ValueError, match="degrees"):
            BeamGeometry(gantry_angle=angle)


def _write_rtplan(path, beams) -> None:  # type: ignore[no-untyped-def]
    """Write a minimal DICOM RT Plan with the given beams (list of dicts)."""
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
        cp.SourceToSurfaceDistance = b.get("ssd", 900.0)
        beam.ControlPointSequence = [cp]
        beam_seq.append(beam)
    ds.BeamSequence = beam_seq

    try:
        ds.save_as(str(path), enforce_file_format=True)
    except TypeError:
        ds.save_as(str(path), write_like_original=False)


@requires_pydicom
class TestLoadBeamGeometry:
    def test_reads_treatment_beams(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        plan = tmp_path / "plan.dcm"
        _write_rtplan(plan, [
            {"number": 1, "name": "AP", "gantry": 0.0, "collimator": 0.0, "couch": 0.0, "energy": 6.0},
            {"number": 2, "name": "LLAT", "gantry": 90.0, "collimator": 45.0, "couch": 10.0, "energy": 10.0},
        ])

        beams = load_beam_geometry(plan)
        assert len(beams) == 2
        assert beams[0].beam_name == "AP"
        assert beams[1].gantry_angle == 90.0
        assert beams[1].collimator_angle == 45.0
        assert beams[1].couch_angle == 10.0
        assert beams[1].beam_energy_mv == 10.0
        assert beams[1].ssd_mm == 900.0

    def test_setup_beams_excluded_by_default(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        plan = tmp_path / "plan.dcm"
        _write_rtplan(plan, [
            {"number": 1, "name": "TX", "gantry": 0.0, "collimator": 0.0, "couch": 0.0},
            {"number": 2, "name": "SETUP", "gantry": 0.0, "collimator": 0.0, "couch": 0.0,
             "delivery": "SETUP"},
        ])

        assert len(load_beam_geometry(plan)) == 1
        assert len(load_beam_geometry(plan, include_setup=True)) == 2

    def test_angles_wrapped_into_range(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """A 360 deg angle from the plan wraps to 0, keeping BeamGeometry valid."""
        plan = tmp_path / "plan.dcm"
        _write_rtplan(plan, [
            {"number": 1, "name": "B", "gantry": 360.0, "collimator": 0.0, "couch": 0.0},
        ])
        assert load_beam_geometry(plan)[0].gantry_angle == 0.0

    def test_empty_elements_do_not_crash(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """Present-but-empty DICOM elements fall back to defaults, not exceptions."""
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

        beam = Dataset()
        beam.BeamNumber = None  # present but empty (Type 2)
        beam.BeamName = None
        cp = Dataset()
        cp.ControlPointIndex = 0
        cp.GantryAngle = None  # empty angle must not raise
        cp.BeamLimitingDeviceAngle = None
        cp.PatientSupportAngle = None
        beam.ControlPointSequence = [cp]
        ds.BeamSequence = [beam]

        plan = tmp_path / "empty.dcm"
        try:
            ds.save_as(str(plan), enforce_file_format=True)
        except TypeError:
            ds.save_as(str(plan), write_like_original=False)

        beams = load_beam_geometry(plan)
        assert len(beams) == 1
        g = beams[0]
        assert g.gantry_angle == 0.0
        assert g.beam_name == ""  # not the string "None"
        assert g.beam_number is None
        assert g.beam_energy_mv is None

    def test_non_rtplan_raises(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import pydicom
        from pydicom.dataset import Dataset, FileMetaDataset
        from pydicom.uid import ExplicitVRLittleEndian, generate_uid

        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.7"
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds = Dataset()
        ds.file_meta = file_meta
        ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.7"
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        not_a_plan = tmp_path / "img.dcm"
        try:
            ds.save_as(str(not_a_plan), enforce_file_format=True)
        except TypeError:
            ds.save_as(str(not_a_plan), write_like_original=False)

        with pytest.raises(ValueError, match="BeamSequence"):
            load_beam_geometry(not_a_plan)
        assert pydicom  # keep import referenced
