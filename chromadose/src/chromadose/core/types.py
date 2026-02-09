"""Core data types for chromadose."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class FilmScan:
    """A scanned film image with RGB channels.

    Attributes:
        red: Red channel pixel values, normalized to [0, 1]. Shape (H, W).
        green: Green channel pixel values, normalized to [0, 1]. Shape (H, W).
        blue: Blue channel pixel values, normalized to [0, 1]. Shape (H, W).
        dpi: Scanner resolution in dots per inch.
    """

    red: NDArray[np.floating]
    green: NDArray[np.floating]
    blue: NDArray[np.floating]
    dpi: float = 72.0

    @property
    def shape(self) -> tuple[int, int]:
        return (self.red.shape[0], self.red.shape[1])

    @property
    def rgb(self) -> NDArray[np.floating]:
        """Stacked (H, W, 3) array of [R, G, B] channels."""
        return np.stack([self.red, self.green, self.blue], axis=-1)

    @property
    def pixel_size_mm(self) -> float:
        """Pixel size in millimeters."""
        return 25.4 / self.dpi


@dataclass(frozen=True)
class CalibrationData:
    """Data extracted from calibration films.

    Attributes:
        doses: Known doses in Gy, shape (n_doses,).
        pixel_values: Mean pixel values per ROI per channel.
            Shape (n_doses, 3) for [R, G, B].
        pre_irrad: Optional pre-irradiation pixel values.
            Shape (n_doses, 3) for [R, G, B]. None if not available.
    """

    doses: NDArray[np.floating]
    pixel_values: NDArray[np.floating]
    pre_irrad: NDArray[np.floating] | None = None

    def __post_init__(self) -> None:
        if self.doses.shape[0] != self.pixel_values.shape[0]:
            raise ValueError(
                f"doses has {self.doses.shape[0]} entries but "
                f"pixel_values has {self.pixel_values.shape[0]} rows"
            )
        if self.pixel_values.ndim != 2 or self.pixel_values.shape[1] != 3:
            raise ValueError(f"pixel_values must be (n_doses, 3), got {self.pixel_values.shape}")

    @property
    def n_doses(self) -> int:
        return len(self.doses)

    @property
    def channels(self) -> int:
        """Number of channels: 3 (RGB) or 6 (RGB pre + RGB post)."""
        return 6 if self.pre_irrad is not None else 3


@dataclass(frozen=True)
class FitParams:
    """Fitted rational function parameters for one channel.

    Model: pixel(D) = (r + s * D) / (t + D)
    """

    r: float
    s: float
    t: float

    def pixel(self, dose: NDArray[np.floating]) -> NDArray[np.floating]:
        """Predict pixel value for given dose."""
        return (self.r + self.s * dose) / (self.t + dose)

    def dose(self, pixel: NDArray[np.floating]) -> NDArray[np.floating]:
        """Invert the rational function: given pixel value, return dose.

        From pixel = (r + s*D) / (t + D), solving for D:
            D = (r - pixel * t) / (pixel - s)
        """
        return (self.r - pixel * self.t) / (pixel - self.s)

    def dpixel_ddose(self, dose: NDArray[np.floating]) -> NDArray[np.floating]:
        """Derivative d(pixel)/d(dose) = (s*t - r) / (t + D)^2."""
        return (self.s * self.t - self.r) / (self.t + dose) ** 2


@dataclass(frozen=True)
class CalibrationResult:
    """Fitted calibration curves for all channels.

    Attributes:
        red: Fit parameters for red channel.
        green: Fit parameters for green channel.
        blue: Fit parameters for blue channel.
        cal_data: The calibration data used for fitting.
    """

    red: FitParams
    green: FitParams
    blue: FitParams
    cal_data: CalibrationData

    def params(self, channel: str) -> FitParams:
        """Get fit params by channel name."""
        return {"red": self.red, "green": self.green, "blue": self.blue}[channel]

    @property
    def dose_range(self) -> tuple[float, float]:
        """Min and max calibrated dose."""
        return (float(self.cal_data.doses.min()), float(self.cal_data.doses.max()))


@dataclass(frozen=True)
class DoseMap:
    """Result of film-to-dose conversion.

    Attributes:
        dose: 2D dose array in Gy, shape (H, W).
        uncertainty: Per-pixel uncertainty estimate in Gy, shape (H, W).
        dose_r: Red channel dose, shape (H, W).
        dose_g: Green channel dose, shape (H, W).
        dose_b: Blue channel dose, shape (H, W).
        method: Name of the method used.
        metadata: Additional info (calibration, film path, etc.).
    """

    dose: NDArray[np.floating]
    uncertainty: NDArray[np.floating]
    dose_r: NDArray[np.floating]
    dose_g: NDArray[np.floating]
    dose_b: NDArray[np.floating]
    method: str = ""
    metadata: dict = field(default_factory=dict)  # type: ignore[type-arg]

    @property
    def shape(self) -> tuple[int, int]:
        return (self.dose.shape[0], self.dose.shape[1])
