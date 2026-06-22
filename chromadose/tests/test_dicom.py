"""Tests for the DICOM RT Dose module.

The RTDose dataclass and resample_to_film are tested with synthetic data and
need no DICOM files. The import/export round-trip tests require pydicom and are
skipped when it is unavailable.
"""

import importlib.util

import numpy as np
import pytest

from chromadose.io.dicom import RTDose, load_dicom_dose, resample_to_film, save_dicom_dose

_HAS_PYDICOM = importlib.util.find_spec("pydicom") is not None
requires_pydicom = pytest.mark.skipif(not _HAS_PYDICOM, reason="pydicom not installed")


class TestRTDose:
    def _make_rtdose(self) -> RTDose:
        """Create a synthetic RT Dose object."""
        dose = np.random.default_rng(42).random((3, 20, 30)) * 5.0
        return RTDose(
            dose=dose,
            pixel_spacing_mm=(2.5, 2.5),
            origin_mm=(0.0, 0.0, 0.0),
            patient_name="Test Patient",
            plan_label="IMRT QA",
        )

    def test_shape(self) -> None:
        rt = self._make_rtdose()
        assert rt.shape == (3, 20, 30)

    def test_n_slices(self) -> None:
        rt = self._make_rtdose()
        assert rt.n_slices == 3

    def test_slice_2d(self) -> None:
        rt = self._make_rtdose()
        s = rt.slice_2d(1)
        assert s.shape == (20, 30)
        np.testing.assert_array_equal(s, rt.dose[1])

    def test_max_dose_slice(self) -> None:
        rt = self._make_rtdose()
        idx, slc = rt.max_dose_slice()
        # Should be the slice with the highest max
        max_per_slice = [np.max(rt.dose[i]) for i in range(3)]
        assert idx == int(np.argmax(max_per_slice))
        assert slc.shape == (20, 30)


class TestResampleToFilm:
    def test_same_resolution_centered(self) -> None:
        """Resampling at the same resolution should give similar values."""
        dose_2d = np.ones((20, 30)) * 2.0
        rt = RTDose(
            dose=dose_2d[np.newaxis],
            pixel_spacing_mm=(1.0, 1.0),
            origin_mm=(0.0, 0.0, 0.0),
        )
        resampled = resample_to_film(rt, film_shape=(20, 30), film_pixel_size_mm=1.0)
        np.testing.assert_allclose(resampled, 2.0, atol=0.01)

    def test_upsampled_preserves_dose(self) -> None:
        """Upsampling a uniform field should still be uniform."""
        dose_2d = np.ones((10, 10)) * 3.0
        rt = RTDose(
            dose=dose_2d[np.newaxis],
            pixel_spacing_mm=(2.0, 2.0),
            origin_mm=(0.0, 0.0, 0.0),
        )
        resampled = resample_to_film(rt, film_shape=(20, 20), film_pixel_size_mm=1.0)
        # Central region should be close to 3.0
        central = resampled[5:15, 5:15]
        np.testing.assert_allclose(central, 3.0, atol=0.01)

    def test_output_shape(self) -> None:
        dose_2d = np.ones((10, 10))
        rt = RTDose(
            dose=dose_2d[np.newaxis],
            pixel_spacing_mm=(1.0, 1.0),
            origin_mm=(0.0, 0.0, 0.0),
        )
        resampled = resample_to_film(rt, film_shape=(30, 40), film_pixel_size_mm=0.5)
        assert resampled.shape == (30, 40)

    def test_gradient_preserved(self) -> None:
        """A linear gradient should be preserved after resampling."""
        x = np.linspace(0, 5, 20)
        dose_2d = np.broadcast_to(x, (20, 20)).copy()
        rt = RTDose(
            dose=dose_2d[np.newaxis],
            pixel_spacing_mm=(1.0, 1.0),
            origin_mm=(0.0, 0.0, 0.0),
        )
        resampled = resample_to_film(rt, film_shape=(20, 20), film_pixel_size_mm=1.0)
        # Central column profile should be roughly linear
        col = resampled[10, 5:15]
        diffs = np.diff(col)
        # All differences should be positive (increasing)
        assert np.all(diffs > -0.1)


@requires_pydicom
class TestSaveDicomDose:
    def test_roundtrip_2d(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """A 2D dose saved and reloaded should match within scaling precision."""
        rng = np.random.default_rng(0)
        dose = rng.random((25, 40)) * 6.0
        out = tmp_path / "dose.dcm"

        save_dicom_dose(
            dose, out,
            pixel_spacing_mm=(0.5, 0.5),
            patient_name="Film QA",
            patient_id="QA001",
            plan_label="VMAT",
        )

        rt = load_dicom_dose(out)
        assert rt.n_slices == 1
        assert rt.pixel_spacing_mm == (0.5, 0.5)
        # uint32 scaling -> effectively lossless at Gy scale.
        np.testing.assert_allclose(rt.slice_2d(0), dose, atol=1e-5)
        assert str(rt.patient_name) == "Film QA"
        assert rt.plan_label == "VMAT"

    def test_roundtrip_3d(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """A 3D dose volume should round-trip with all slices preserved."""
        rng = np.random.default_rng(1)
        dose = rng.random((4, 10, 12)) * 3.0
        out = tmp_path / "vol.dcm"

        save_dicom_dose(dose, out, slice_spacing_mm=2.0)

        rt = load_dicom_dose(out)
        assert rt.shape == (4, 10, 12)
        np.testing.assert_allclose(rt.dose, dose, atol=1e-5)

    def test_zero_dose(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """An all-zero dose must not divide by zero and round-trips to zero."""
        out = tmp_path / "zero.dcm"
        save_dicom_dose(np.zeros((8, 8)), out)
        rt = load_dicom_dose(out)
        np.testing.assert_array_equal(rt.slice_2d(0), np.zeros((8, 8)))

    def test_invalid_ndim(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        """A 1D array should raise ValueError."""
        with pytest.raises(ValueError, match="2D or 3D"):
            save_dicom_dose(np.zeros(5), tmp_path / "bad.dcm")
