"""High-level Calibration class."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from numpy.typing import NDArray

from chromadose.calibration.curves import fit_all_channels, rational_function
from chromadose.core.types import CalibrationData, CalibrationResult, FitParams


class Calibration:
    """Film calibration: fits dose-response curves from calibration data.

    This is the main entry point for calibrating radiochromic films.

    Example:
        >>> cal_data = CalibrationData(
        ...     doses=np.array([0, 0.5, 1, 2, 4, 7, 9]),
        ...     pixel_values=np.array([...]),  # shape (7, 3) for RGB
        ... )
        >>> cal = Calibration(cal_data)
        >>> cal.result.red  # FitParams for red channel
        FitParams(r=0.655, s=0.037, t=2.956)
    """

    def __init__(self, cal_data: CalibrationData) -> None:
        self.cal_data = cal_data
        red, green, blue = fit_all_channels(cal_data.doses, cal_data.pixel_values)
        self.result = CalibrationResult(
            red=red, green=green, blue=blue, cal_data=cal_data
        )

    @classmethod
    def from_arrays(
        cls,
        doses: list[float] | NDArray[np.floating],
        red_pixels: list[float] | NDArray[np.floating],
        green_pixels: list[float] | NDArray[np.floating],
        blue_pixels: list[float] | NDArray[np.floating],
    ) -> Calibration:
        """Create calibration from raw dose and pixel value arrays.

        This is the simplest way to calibrate — provide doses and mean pixel
        values directly (e.g., extracted manually from ROIs).

        Parameters:
            doses: Dose values in Gy.
            red_pixels: Mean red channel pixel values (0-1 normalized).
            green_pixels: Mean green channel pixel values (0-1 normalized).
            blue_pixels: Mean blue channel pixel values (0-1 normalized).
        """
        doses_arr = np.asarray(doses, dtype=np.float64)
        pixels = np.column_stack([
            np.asarray(red_pixels, dtype=np.float64),
            np.asarray(green_pixels, dtype=np.float64),
            np.asarray(blue_pixels, dtype=np.float64),
        ])

        # Sort by dose (low to high)
        sort_idx = np.argsort(doses_arr)
        cal_data = CalibrationData(
            doses=doses_arr[sort_idx],
            pixel_values=pixels[sort_idx],
        )
        return cls(cal_data)

    def save(self, path: str | Path) -> None:
        """Save calibration to a JSON file."""
        data = {
            "version": "chromadose-1.0",
            "doses": self.cal_data.doses.tolist(),
            "pixel_values": self.cal_data.pixel_values.tolist(),
            "fit_params": {
                "red": {"r": self.result.red.r, "s": self.result.red.s, "t": self.result.red.t},
                "green": {
                    "r": self.result.green.r,
                    "s": self.result.green.s,
                    "t": self.result.green.t,
                },
                "blue": {
                    "r": self.result.blue.r,
                    "s": self.result.blue.s,
                    "t": self.result.blue.t,
                },
            },
        }
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> Calibration:
        """Load calibration from a JSON file."""
        data = json.loads(Path(path).read_text())
        cal = cls.__new__(cls)
        cal.cal_data = CalibrationData(
            doses=np.array(data["doses"]),
            pixel_values=np.array(data["pixel_values"]),
        )
        fp = data["fit_params"]
        cal.result = CalibrationResult(
            red=FitParams(**fp["red"]),
            green=FitParams(**fp["green"]),
            blue=FitParams(**fp["blue"]),
            cal_data=cal.cal_data,
        )
        return cal

    def plot_curves(self, ax: Axes | None = None) -> Figure:
        """Plot calibration data points and fitted curves."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 5))
        else:
            parent = ax.get_figure()
            # ax.get_figure() returns Figure | SubFigure | None; narrow to Figure.
            if not isinstance(parent, Figure):
                raise TypeError("Axes must belong to a top-level Figure, not a SubFigure")
            fig = parent

        doses = self.cal_data.doses
        pixels = self.cal_data.pixel_values
        d_fine = np.linspace(0, doses.max() * 1.1, 200)

        colors = {"red": "r", "green": "g", "blue": "b"}
        for i, (name, color) in enumerate(colors.items()):
            params = self.result.params(name)
            ax.scatter(doses, pixels[:, i], c=color, label=f"{name} data", zorder=3)
            ax.plot(d_fine, rational_function(d_fine, params.r, params.s, params.t),
                    c=color, alpha=0.7)

        ax.set_xlabel("Dose (Gy)")
        ax.set_ylabel("Pixel value (normalized)")
        ax.set_title("Calibration Curves — pixel(D) = (r + sD) / (t + D)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        return fig

    def summary(self) -> str:
        """Return a text summary of the calibration."""
        lines = [
            "Calibration Summary",
            "=" * 40,
            f"Dose range: {self.result.dose_range[0]:.2f} - {self.result.dose_range[1]:.2f} Gy",
            f"Number of dose points: {self.cal_data.n_doses}",
            f"Channels: {self.cal_data.channels}",
            "",
            "Fit Parameters — pixel(D) = (r + sD) / (t + D):",
            f"  Red:   r={self.result.red.r:.6f}, s={self.result.red.s:.6f}, t={self.result.red.t:.6f}",
            f"  Green: r={self.result.green.r:.6f}, s={self.result.green.s:.6f}, t={self.result.green.t:.6f}",
            f"  Blue:  r={self.result.blue.r:.6f}, s={self.result.blue.s:.6f}, t={self.result.blue.t:.6f}",
        ]
        return "\n".join(lines)
