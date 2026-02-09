"""Multigaussian method (Mendez et al., 2018) for multichannel film dosimetry.

Based on:
    Mendez I, Polsak A, Hudej R, Casar B. "The Multigaussian method: a new
    approach to mitigating spatial heterogeneities with multichannel
    radiochromic film dosimetry." Phys. Med. Biol. 2018;63(17):175013.
    arXiv: 1804.03885

THIS IS THE FIRST OPEN-SOURCE IMPLEMENTATION OF THIS METHOD.

The Multigaussian method models the joint probability distribution of the
response vector (pixel values across all color channels) as a multivariate
Gaussian distribution at each dose level:

    p(x | D) = N(x; μ(D), Σ(D))

Where:
    x = response vector [R, G, B] (or [R_pre, G_pre, B_pre, R, G, B] with pre-scan)
    μ(D) = mean response vector at dose D
    Σ(D) = covariance matrix of response at dose D

Dose estimation is by maximum likelihood (equivalently, minimize the
Mahalanobis distance plus log-determinant of covariance):

    D* = argmin_D [ (x - μ(D))ᵀ Σ(D)⁻¹ (x - μ(D)) + ln|Σ(D)| ]

Key advantages over Micke/Mayer:
    - Uses the FULL covariance structure (not just per-channel info)
    - Naturally handles correlations between channels
    - Can incorporate pre-irradiation scans (6-channel mode)
    - Provides principled uncertainty from the probabilistic model
    - Demonstrated 0.8% mean absolute error (best published result)
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from chromadose.core.types import CalibrationResult, DoseMap, FilmScan


class MultigaussianCalibration:
    """Calibration data for the Multigaussian method.

    Instead of fitting per-channel rational functions, this stores the
    mean response vector and covariance matrix at each calibration dose,
    then interpolates them as continuous functions of dose.

    Parameters:
        doses: Calibration doses in Gy, shape (n_doses,).
        pixel_samples: Per-ROI pixel values for each dose level.
            Shape (n_doses, n_samples, n_channels).
            n_samples = number of pixels sampled from each calibration ROI.
            n_channels = 3 (RGB) or 6 (RGB pre + RGB post).
    """

    def __init__(
        self,
        doses: NDArray[np.floating],
        pixel_samples: NDArray[np.floating],
    ) -> None:
        sort_idx = np.argsort(doses)
        self.doses = doses[sort_idx]
        self.pixel_samples = pixel_samples[sort_idx]
        self.n_doses = len(self.doses)
        self.n_channels = self.pixel_samples.shape[2]

        # Compute mean vectors and covariance matrices at each dose
        self.means = np.zeros((self.n_doses, self.n_channels))
        self.covs = np.zeros((self.n_doses, self.n_channels, self.n_channels))

        for i in range(self.n_doses):
            samples = self.pixel_samples[i]  # (n_samples, n_channels)
            self.means[i] = np.mean(samples, axis=0)
            self.covs[i] = np.cov(samples, rowvar=False)

            # Regularize covariance to ensure positive definiteness
            self.covs[i] += np.eye(self.n_channels) * 1e-8

        # Precompute inverses and log-determinants
        self.cov_invs = np.zeros_like(self.covs)
        self.log_dets = np.zeros(self.n_doses)
        for i in range(self.n_doses):
            self.cov_invs[i] = np.linalg.inv(self.covs[i])
            self.log_dets[i] = np.log(np.linalg.det(self.covs[i]))

        # Build interpolators for mean, covariance inverse, and log-det
        # as continuous functions of dose
        self._interp_mean = interp1d(
            self.doses, self.means, axis=0,
            kind="linear", fill_value="extrapolate",
        )
        self._interp_cov_inv = interp1d(
            self.doses, self.cov_invs, axis=0,
            kind="linear", fill_value="extrapolate",
        )
        self._interp_log_det = interp1d(
            self.doses, self.log_dets, axis=0,
            kind="linear", fill_value="extrapolate",
        )

    def mean_at(self, dose: float) -> NDArray[np.floating]:
        """Interpolated mean response vector at given dose."""
        return self._interp_mean(dose)

    def cov_inv_at(self, dose: float) -> NDArray[np.floating]:
        """Interpolated inverse covariance matrix at given dose."""
        return self._interp_cov_inv(dose)

    def log_det_at(self, dose: float) -> float:
        """Interpolated log-determinant of covariance at given dose."""
        return float(self._interp_log_det(dose))

    @classmethod
    def from_film_rois(
        cls,
        doses: NDArray[np.floating],
        films: list[FilmScan],
        rois: list[tuple[int, int, int, int]],
        pre_films: list[FilmScan] | None = None,
    ) -> MultigaussianCalibration:
        """Build calibration from film scans and ROI definitions.

        Parameters:
            doses: Dose values in Gy, one per ROI.
            films: Post-irradiation film scans.
            rois: List of (x, y, width, height) tuples for each dose level.
            pre_films: Optional pre-irradiation scans. If provided, builds
                a 6-channel calibration [R_pre, G_pre, B_pre, R_post, G_post, B_post].

        Returns:
            MultigaussianCalibration with per-dose statistics (3 or 6 channels).
        """
        pixel_samples_list = []

        for i, (x, y, w, h) in enumerate(rois):
            film = films[i] if len(films) > 1 else films[0]
            r_roi = film.red[y : y + h, x : x + w].flatten()
            g_roi = film.green[y : y + h, x : x + w].flatten()
            b_roi = film.blue[y : y + h, x : x + w].flatten()

            if pre_films is not None:
                pre = pre_films[i] if len(pre_films) > 1 else pre_films[0]
                rp = pre.red[y : y + h, x : x + w].flatten()
                gp = pre.green[y : y + h, x : x + w].flatten()
                bp = pre.blue[y : y + h, x : x + w].flatten()
                samples = np.column_stack([rp, gp, bp, r_roi, g_roi, b_roi])
            else:
                samples = np.column_stack([r_roi, g_roi, b_roi])

            pixel_samples_list.append(samples)

        # Pad to same number of samples (use smallest ROI size)
        min_samples = min(s.shape[0] for s in pixel_samples_list)
        pixel_samples = np.array([s[:min_samples] for s in pixel_samples_list])

        return cls(doses=np.asarray(doses), pixel_samples=pixel_samples)


class MultigaussianSolver:
    """Dose solver using the Multigaussian method (Mendez 2018).

    This is the first open-source implementation of this method.
    """

    def __init__(self, mg_cal: MultigaussianCalibration) -> None:
        self.mg_cal = mg_cal

    def solve(self, film: FilmScan, calibration: CalibrationResult) -> DoseMap:
        """Convert scanned film to dose using Multigaussian MLE (3-channel).

        Parameters:
            film: Scanned film with normalized RGB channels.
            calibration: Standard calibration (used for dose range and per-channel doses).

        Returns:
            DoseMap with Multigaussian-optimized dose.
        """
        d_min, d_max = calibration.dose_range
        H, W = film.shape

        # Per-channel doses (for comparison / fallback)
        dose_r = np.clip(calibration.red.dose(film.red), 0, d_max * 1.5)
        dose_g = np.clip(calibration.green.dose(film.green), 0, d_max * 1.5)
        dose_b = np.clip(calibration.blue.dose(film.blue), 0, d_max * 1.5)

        # Vectorized Multigaussian dose estimation
        pixels_flat = film.rgb.reshape(-1, 3)
        dose_opt, uncertainty = self._solve_from_pixels(pixels_flat, H, W, d_min, d_max)

        return DoseMap(
            dose=dose_opt,
            uncertainty=uncertainty,
            dose_r=dose_r,
            dose_g=dose_g,
            dose_b=dose_b,
            method="multigaussian",
        )

    def solve_6channel(
        self,
        film: FilmScan,
        pre_film: FilmScan,
        calibration: CalibrationResult,
    ) -> DoseMap:
        """Convert scanned film to dose using 6-channel Multigaussian MLE.

        Uses both pre-irradiation and post-irradiation scans for improved
        accuracy. The response vector is [R_pre, G_pre, B_pre, R_post, G_post, B_post].

        Parameters:
            film: Post-irradiation film scan.
            pre_film: Pre-irradiation film scan (same film, scanned before exposure).
            calibration: Standard calibration (for dose range and per-channel comparison).

        Returns:
            DoseMap with 6-channel Multigaussian-optimized dose.
        """
        if self.mg_cal.n_channels != 6:
            raise ValueError(
                f"6-channel solve requires a 6-channel calibration, "
                f"but calibration has {self.mg_cal.n_channels} channels"
            )

        d_min, d_max = calibration.dose_range
        H, W = film.shape

        dose_r = np.clip(calibration.red.dose(film.red), 0, d_max * 1.5)
        dose_g = np.clip(calibration.green.dose(film.green), 0, d_max * 1.5)
        dose_b = np.clip(calibration.blue.dose(film.blue), 0, d_max * 1.5)

        # Stack 6-channel pixel array: [R_pre, G_pre, B_pre, R_post, G_post, B_post]
        pixels_6ch = np.stack([
            pre_film.red, pre_film.green, pre_film.blue,
            film.red, film.green, film.blue,
        ], axis=-1)  # (H, W, 6)
        pixels_flat = pixels_6ch.reshape(-1, 6)

        dose_opt, uncertainty = self._solve_from_pixels(pixels_flat, H, W, d_min, d_max)

        return DoseMap(
            dose=dose_opt,
            uncertainty=uncertainty,
            dose_r=dose_r,
            dose_g=dose_g,
            dose_b=dose_b,
            method="multigaussian-6ch",
        )

    def _solve_from_pixels(
        self,
        pixels_flat: NDArray[np.floating],
        H: int,
        W: int,
        d_min: float,
        d_max: float,
    ) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
        """Solve for dose at every pixel — fully vectorized, no per-pixel loops.

        Works with any number of channels (3 for RGB, 6 for pre+post).

        Strategy:
        1. Evaluate NLL on a dense dose grid for ALL pixels simultaneously
        2. Find the best grid point per pixel
        3. Vectorized parabolic interpolation from 3 neighboring grid points
        4. Compute uncertainty from the same grid NLL curvature (free!)

        Parameters:
            pixels_flat: (N, n_channels) pixel values.
            H, W: Image dimensions for reshaping output.
            d_min, d_max: Dose search range.

        Returns:
            Tuple of (dose, uncertainty) each shape (H, W).
        """
        N = pixels_flat.shape[0]

        # Dense grid for accuracy without per-pixel refinement
        n_grid = 200
        dose_grid = np.linspace(d_min, d_max, n_grid)
        grid_step = dose_grid[1] - dose_grid[0]

        # Evaluate NLL at each grid point for all pixels simultaneously
        nll = np.zeros((N, n_grid))
        for j, d in enumerate(dose_grid):
            nll[:, j] = self._nll_batch(pixels_flat, d)

        # Find best grid point per pixel
        best_idx = np.argmin(nll, axis=1)  # (N,)

        # Vectorized parabolic interpolation from 3 neighboring points
        # Clamp indices so we have valid left/right neighbors
        idx_left = np.clip(best_idx - 1, 0, n_grid - 1)
        idx_right = np.clip(best_idx + 1, 0, n_grid - 1)

        d_left = dose_grid[idx_left]
        d_center = dose_grid[best_idx]
        d_right = dose_grid[idx_right]

        # NLL at the three points
        pixel_idx = np.arange(N)
        f_left = nll[pixel_idx, idx_left]
        f_center = nll[pixel_idx, best_idx]
        f_right = nll[pixel_idx, idx_right]

        # Parabolic interpolation: vertex of parabola through 3 points
        num = (d_right - d_left) * (f_right - f_left)
        denom = 2.0 * (2.0 * f_center - f_left - f_right)
        safe_denom = np.where(np.abs(denom) > 1e-20, denom, 1.0)
        shift = np.where(np.abs(denom) > 1e-20, num / safe_denom, 0.0)
        dose_refined = d_center - 0.5 * shift
        dose_refined = np.clip(dose_refined, d_min, d_max)

        # Uncertainty from NLL curvature at the 3 grid points (free — already computed)
        # d²NLL/dD² ≈ (f_left - 2*f_center + f_right) / h²
        d2nll = (f_left - 2.0 * f_center + f_right) / (grid_step ** 2)
        d2nll = np.where(d2nll > 1e-10, d2nll, 1e-10)
        uncertainty = np.sqrt(1.0 / d2nll)

        return dose_refined.reshape(H, W), uncertainty.reshape(H, W)

    def _nll_batch(
        self,
        pixels: NDArray[np.floating],
        dose: float,
    ) -> NDArray[np.floating]:
        """Negative log-likelihood for all pixels at a single dose.

        NLL(x, D) = (x - μ(D))ᵀ Σ(D)⁻¹ (x - μ(D)) + ln|Σ(D)|

        Parameters:
            pixels: (N, n_channels) pixel values.
            dose: Single dose value.

        Returns:
            (N,) negative log-likelihood values.
        """
        mu = self.mg_cal.mean_at(dose)  # (n_channels,)
        cov_inv = self.mg_cal.cov_inv_at(dose)  # (n_channels, n_channels)
        log_det = self.mg_cal.log_det_at(dose)

        diff = pixels - mu  # (N, n_channels)
        mahal = np.sum(diff @ cov_inv * diff, axis=1)  # (N,)

        return mahal + log_det

