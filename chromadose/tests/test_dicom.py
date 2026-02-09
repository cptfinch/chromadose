"""Tests for the DICOM RT Dose module.

Since pydicom may not be available in all environments and we don't want
to depend on actual DICOM files, we test the RTDose dataclass and the
resample_to_film function with synthetic data.
"""

import numpy as np

from chromadose.io.dicom import RTDose, resample_to_film


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
