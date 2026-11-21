"""Tests for TIFF loading, in particular where the film's DPI comes from."""

from pathlib import Path

import numpy as np
import pytest
import tifffile

from chromadose.core.image import load_tiff, load_tiff_averaged


def _write(path: Path, **kwargs: object) -> Path:
    """Write a small RGB TIFF with the given resolution tags."""
    tifffile.imwrite(path, np.zeros((8, 8, 3), np.uint16), photometric="rgb", **kwargs)
    return path


class TestFilmDpi:
    def test_inches(self, tmp_path: Path) -> None:
        scan = load_tiff(_write(tmp_path / "a.tif", resolution=(150, 150), resolutionunit="INCH"))
        assert scan.dpi == pytest.approx(150.0)
        assert not scan.dpi_assumed
        assert scan.pixel_size_mm == pytest.approx(25.4 / 150)

    def test_centimetres_are_converted(self, tmp_path: Path) -> None:
        """Pixels per centimetre used to be read as pixels per inch (2.54x too coarse)."""
        per_cm = 150 / 2.54
        scan = load_tiff(
            _write(tmp_path / "a.tif", resolution=(per_cm, per_cm), resolutionunit="CENTIMETER")
        )
        assert scan.dpi == pytest.approx(150.0, rel=1e-3)
        assert not scan.dpi_assumed
        assert scan.pixel_size_mm == pytest.approx(25.4 / 150, rel=1e-3)

    def test_no_resolution_is_assumed_72(self, tmp_path: Path) -> None:
        """tifffile writes 1/1 with unit NONE by default; that used to read as 1 dpi (25.4 mm)."""
        scan = load_tiff(_write(tmp_path / "a.tif"))
        assert scan.dpi == 72.0
        assert scan.dpi_assumed
        assert scan.pixel_size_mm == pytest.approx(25.4 / 72)

    def test_unit_none_carries_no_scale(self, tmp_path: Path) -> None:
        """With unit NONE the numbers are only an aspect ratio, so the value is not trusted."""
        scan = load_tiff(_write(tmp_path / "a.tif", resolution=(150, 150), resolutionunit="NONE"))
        assert scan.dpi == 72.0
        assert scan.dpi_assumed

    def test_grayscale_scan_carries_the_flag(self, tmp_path: Path) -> None:
        path = tmp_path / "gray.tif"
        tifffile.imwrite(path, np.zeros((8, 8), np.uint16), resolution=(300, 300), resolutionunit="INCH")
        scan = load_tiff(path)
        assert scan.dpi == pytest.approx(300.0)
        assert not scan.dpi_assumed

    def test_a_directly_built_scan_is_not_flagged(self) -> None:
        from chromadose.core.types import FilmScan

        ones = np.ones((4, 4))
        assert not FilmScan(red=ones, green=ones, blue=ones, dpi=150).dpi_assumed


class TestAveraged:
    def test_keeps_dpi_and_flag(self, tmp_path: Path) -> None:
        paths = [
            _write(tmp_path / f"{i}.tif", resolution=(150, 150), resolutionunit="INCH")
            for i in range(2)
        ]
        scan = load_tiff_averaged(list(paths))
        assert scan.dpi == pytest.approx(150.0)
        assert not scan.dpi_assumed

    def test_assumed_flag_survives_averaging(self, tmp_path: Path) -> None:
        scan = load_tiff_averaged([_write(tmp_path / f"{i}.tif") for i in range(2)])
        assert scan.dpi_assumed
