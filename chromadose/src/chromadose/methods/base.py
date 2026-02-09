"""Base protocol for dose solving methods."""

from __future__ import annotations

from typing import Protocol

from chromadose.core.types import CalibrationResult, DoseMap, FilmScan


class DoseSolver(Protocol):
    """Interface that all dose solving methods must implement.

    Each method (Micke, Mayer, Multigaussian, ANN) implements this protocol
    to provide a consistent API for converting scanned films to dose maps.
    """

    def solve(self, film: FilmScan, calibration: CalibrationResult) -> DoseMap:
        """Convert a scanned film to a dose map using the calibrated curves.

        Parameters:
            film: Scanned film with RGB channels.
            calibration: Fitted calibration curves.

        Returns:
            DoseMap with the optimized dose and per-channel doses.
        """
        ...
