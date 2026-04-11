"""Neural network dose solver (Chang et al., 2021/2025).

Based on:
    Chang L-Y, et al. "GANN: a generalized artificial neural network for
    multichannel radiochromic film dosimetry." Phys. Med. Biol. 2025.

This implements a lightweight feedforward neural network that maps
RGB pixel values directly to dose. Key advantages:

- Can learn nonlinear calibration relationships without rational function assumptions
- Potentially batch-independent when trained on multiple film batches
- Uncertainty estimation via ensemble of networks

Architecture:
    Input:  [R, G, B] pixel values (3 neurons)
    Hidden: 2 layers of 32 neurons each, ReLU activation
    Output: dose (1 neuron, ReLU to enforce non-negativity)

This implementation uses pure numpy + scipy for zero extra dependencies.
For production use with larger datasets, consider PyTorch (`chromadose[ann]`).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from chromadose.core.types import CalibrationResult, DoseMap, FilmScan


@dataclass
class ANNWeights:
    """Weights for a feedforward neural network.

    Architecture: input(3) -> hidden1(n_hidden) -> hidden2(n_hidden) -> output(1)
    """

    W1: NDArray[np.floating]  # (3, n_hidden)
    b1: NDArray[np.floating]  # (n_hidden,)
    W2: NDArray[np.floating]  # (n_hidden, n_hidden)
    b2: NDArray[np.floating]  # (n_hidden,)
    W3: NDArray[np.floating]  # (n_hidden, 1)
    b3: NDArray[np.floating]  # (1,)

    @property
    def n_hidden(self) -> int:
        return self.W1.shape[1]

    @property
    def n_params(self) -> int:
        return sum(w.size for w in [self.W1, self.b1, self.W2, self.b2, self.W3, self.b3])

    def to_vector(self) -> NDArray[np.floating]:
        """Flatten all weights into a single parameter vector."""
        return np.concatenate([
            self.W1.ravel(), self.b1.ravel(),
            self.W2.ravel(), self.b2.ravel(),
            self.W3.ravel(), self.b3.ravel(),
        ])

    @classmethod
    def from_vector(cls, vec: NDArray[np.floating], n_input: int = 3, n_hidden: int = 32) -> ANNWeights:
        """Reconstruct weights from a flat parameter vector."""
        idx = 0

        W1 = vec[idx:idx + n_input * n_hidden].reshape(n_input, n_hidden)
        idx += n_input * n_hidden
        b1 = vec[idx:idx + n_hidden]
        idx += n_hidden

        W2 = vec[idx:idx + n_hidden * n_hidden].reshape(n_hidden, n_hidden)
        idx += n_hidden * n_hidden
        b2 = vec[idx:idx + n_hidden]
        idx += n_hidden

        W3 = vec[idx:idx + n_hidden * 1].reshape(n_hidden, 1)
        idx += n_hidden * 1
        b3 = vec[idx:idx + 1]

        return cls(W1=W1, b1=b1, W2=W2, b2=b2, W3=W3, b3=b3)

    @classmethod
    def random_init(cls, n_input: int = 3, n_hidden: int = 32, seed: int = 42) -> ANNWeights:
        """He initialization for ReLU networks."""
        rng = np.random.default_rng(seed)
        return cls(
            W1=rng.normal(0, np.sqrt(2.0 / n_input), (n_input, n_hidden)),
            b1=np.zeros(n_hidden),
            W2=rng.normal(0, np.sqrt(2.0 / n_hidden), (n_hidden, n_hidden)),
            b2=np.zeros(n_hidden),
            W3=rng.normal(0, np.sqrt(2.0 / n_hidden), (n_hidden, 1)),
            b3=np.zeros(1),
        )


def _relu(x: NDArray[np.floating]) -> NDArray[np.floating]:
    return np.maximum(0, x)


def _forward(rgb: NDArray[np.floating], weights: ANNWeights) -> NDArray[np.floating]:
    """Forward pass: RGB pixels -> dose.

    Parameters:
        rgb: (N, 3) pixel values.
        weights: Network weights.

    Returns:
        (N,) predicted dose values.
    """
    h1 = _relu(rgb @ weights.W1 + weights.b1)       # (N, n_hidden)
    h2 = _relu(h1 @ weights.W2 + weights.b2)        # (N, n_hidden)
    out = (h2 @ weights.W3 + weights.b3).ravel()     # (N,)
    return _relu(out)  # Non-negative dose


class ANNCalibration:
    """Train a neural network for film-to-dose calibration.

    Parameters:
        n_hidden: Number of neurons in each hidden layer.
        n_ensemble: Number of networks to train for uncertainty estimation.
        max_iter: Maximum L-BFGS-B iterations per network.
        seed: Random seed for reproducibility.
    """

    def __init__(
        self,
        n_hidden: int = 32,
        n_ensemble: int = 5,
        max_iter: int = 500,
        seed: int = 42,
    ) -> None:
        self.n_hidden = n_hidden
        self.n_ensemble = n_ensemble
        self.max_iter = max_iter
        self.seed = seed
        self.ensemble: list[ANNWeights] = []

    def fit(
        self,
        pixels: NDArray[np.floating],
        doses: NDArray[np.floating],
    ) -> ANNCalibration:
        """Train the network ensemble on calibration data.

        Parameters:
            pixels: (N, 3) RGB pixel values from calibration ROIs.
            doses: (N,) corresponding doses in Gy.

        Returns:
            self, for method chaining.
        """
        self.ensemble = []
        rng = np.random.default_rng(self.seed)

        # Normalize inputs for better convergence
        self._pixel_mean = np.mean(pixels, axis=0)
        self._pixel_std = np.std(pixels, axis=0)
        self._pixel_std = np.where(self._pixel_std > 1e-8, self._pixel_std, 1.0)
        self._dose_scale = np.max(doses) if np.max(doses) > 0 else 1.0

        pixels_norm = (pixels - self._pixel_mean) / self._pixel_std
        doses_norm = doses / self._dose_scale

        for i in range(self.n_ensemble):
            seed_i = int(rng.integers(0, 2**31))
            weights = ANNWeights.random_init(n_input=3, n_hidden=self.n_hidden, seed=seed_i)

            # Bootstrap sampling for diversity
            n = len(doses)
            idx = rng.choice(n, size=n, replace=True)
            px_boot = pixels_norm[idx]
            d_boot = doses_norm[idx]

            # L-BFGS-B optimization
            def loss_and_grad(
                vec: NDArray[np.floating],
            ) -> tuple[float, NDArray[np.floating]]:
                w = ANNWeights.from_vector(vec, n_input=3, n_hidden=self.n_hidden)
                pred = _forward(px_boot, w)
                residual = pred - d_boot
                mse = float(np.mean(residual ** 2))

                # Numerical gradient (more robust than hand-coded backprop)
                grad = np.zeros_like(vec)
                eps = 1e-5
                for j in range(len(vec)):
                    vec_p = vec.copy()
                    vec_p[j] += eps
                    w_p = ANNWeights.from_vector(vec_p, n_input=3, n_hidden=self.n_hidden)
                    pred_p = _forward(px_boot, w_p)
                    mse_p = float(np.mean((pred_p - d_boot) ** 2))
                    grad[j] = (mse_p - mse) / eps

                return mse, grad

            x0 = weights.to_vector()
            result = minimize(
                loss_and_grad, x0,
                method="L-BFGS-B", jac=True,
                options={"maxiter": self.max_iter, "ftol": 1e-10},
            )

            self.ensemble.append(
                ANNWeights.from_vector(result.x, n_input=3, n_hidden=self.n_hidden)
            )

        return self

    def predict(
        self, pixels: NDArray[np.floating]
    ) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
        """Predict dose from pixel values using the ensemble.

        Parameters:
            pixels: (N, 3) RGB pixel values.

        Returns:
            Tuple of (mean_dose, uncertainty) each shape (N,).
        """
        pixels_norm = (pixels - self._pixel_mean) / self._pixel_std

        predictions = np.array([
            _forward(pixels_norm, w) * self._dose_scale
            for w in self.ensemble
        ])  # (n_ensemble, N)

        mean_dose = np.mean(predictions, axis=0)
        uncertainty = np.std(predictions, axis=0)

        return mean_dose, uncertainty


class ANNSolver:
    """Dose solver using a trained neural network.

    Parameters:
        ann_cal: A trained ANNCalibration instance.
    """

    def __init__(self, ann_cal: ANNCalibration) -> None:
        self.ann_cal = ann_cal

    def solve(self, film: FilmScan, calibration: CalibrationResult) -> DoseMap:
        """Convert scanned film to dose using the neural network.

        Parameters:
            film: Scanned film with normalized RGB channels.
            calibration: Standard calibration (used for per-channel dose comparison).

        Returns:
            DoseMap with ANN-estimated dose and ensemble uncertainty.
        """
        H, W = film.shape
        rgb_flat = film.rgb.reshape(-1, 3)

        # ANN prediction
        dose_flat, unc_flat = self.ann_cal.predict(rgb_flat)

        # Per-channel doses from standard calibration (for comparison)
        d_min, d_max = calibration.dose_range
        dose_r = np.clip(calibration.red.dose(film.red), 0, d_max * 1.5)
        dose_g = np.clip(calibration.green.dose(film.green), 0, d_max * 1.5)
        dose_b = np.clip(calibration.blue.dose(film.blue), 0, d_max * 1.5)

        return DoseMap(
            dose=np.clip(dose_flat.reshape(H, W), 0, d_max * 1.5),
            uncertainty=unc_flat.reshape(H, W),
            dose_r=dose_r,
            dose_g=dose_g,
            dose_b=dose_b,
            method="ann",
            metadata={
                "n_ensemble": len(self.ann_cal.ensemble),
                "n_hidden": self.ann_cal.n_hidden,
            },
        )
