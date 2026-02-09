"""Tests for the film-to-TPS registration module."""

import numpy as np

from chromadose.analysis.registration import (
    apply_rigid_transform,
    register_auto,
    register_manual,
)


class TestRigidTransform:
    def test_identity_transform(self) -> None:
        """Zero translation and rotation should return the same image."""
        image = np.random.default_rng(42).random((20, 30))
        result = apply_rigid_transform(image, dx_px=0, dy_px=0, angle_deg=0)
        np.testing.assert_allclose(result, image, atol=1e-10)

    def test_translation_shifts_image(self) -> None:
        """A known translation should shift content predictably."""
        image = np.zeros((30, 30))
        image[10:20, 10:20] = 1.0  # square block in center

        # Shift right by 5 pixels
        shifted = apply_rigid_transform(image, dx_px=5, dy_px=0, angle_deg=0)
        # The block should now be at columns 15:25
        assert np.mean(shifted[10:20, 15:25]) > 0.8
        assert np.mean(shifted[10:20, 5:10]) < 0.2

    def test_rotation_preserves_total_mass(self) -> None:
        """Small rotation should approximately preserve total sum."""
        image = np.zeros((40, 40))
        image[15:25, 15:25] = 2.0

        rotated = apply_rigid_transform(image, dx_px=0, dy_px=0, angle_deg=5)
        # Total should be similar (small angle, all content stays in frame)
        np.testing.assert_allclose(np.sum(rotated), np.sum(image), rtol=0.05)


class TestAutoRegistration:
    def test_recovers_known_translation(self) -> None:
        """Auto-registration should recover a known translation."""
        # Create a 2D Gaussian blob pattern (rich spatial info in both axes)
        y, x = np.mgrid[0:60, 0:60].astype(np.float64)
        ref = 3.0 * np.exp(-((x - 30)**2 + (y - 30)**2) / (2 * 8**2))

        # Shift by 3px in x = 3mm (pixel_size=1mm)
        evaluated = apply_rigid_transform(ref, dx_px=3, dy_px=2, angle_deg=0)

        result = register_auto(
            ref, evaluated,
            pixel_size_mm=1.0,
            max_shift_mm=10.0,
        )

        # Should recover approximately -3mm, -2mm shift
        np.testing.assert_allclose(result.dx_mm, -3.0, atol=1.0)
        np.testing.assert_allclose(result.dy_mm, -2.0, atol=1.0)

    def test_shape_mismatch_raises(self) -> None:
        ref = np.ones((10, 10))
        evl = np.ones((10, 20))
        try:
            register_auto(ref, evl)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestManualRegistration:
    def test_returns_transformed_image(self) -> None:
        image = np.ones((20, 20)) * 2.0
        result = register_manual(image, dx_mm=1.0, dy_mm=0.0, pixel_size_mm=0.5)
        assert result.registered.shape == (20, 20)
        assert result.dx_mm == 1.0

    def test_zero_transform_preserves_image(self) -> None:
        image = np.random.default_rng(42).random((15, 15))
        result = register_manual(image, dx_mm=0, dy_mm=0, angle_deg=0)
        np.testing.assert_allclose(result.registered, image, atol=1e-10)
