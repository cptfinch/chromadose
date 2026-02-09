# Multigaussian Method (2018)

!!! success "First Open-Source Implementation"
    chromadose provides the **first open-source implementation** of the Multigaussian method.

!!! info "Reference"
    Mendez I, Polsak A, Hudej R, Casar B. "The Multigaussian method: a new approach to mitigating spatial heterogeneities with multichannel radiochromic film dosimetry." *Phys. Med. Biol.* 2018;63(17):175013.

## Theory

Models the full joint probability distribution of pixel values as a multivariate Gaussian at each dose:

$$p(\mathbf{x} | D) = \mathcal{N}(\mathbf{x}; \boldsymbol{\mu}(D), \boldsymbol{\Sigma}(D))$$

Dose estimation by maximum likelihood:

$$D^* = \arg\min_D \left[ (\mathbf{x} - \boldsymbol{\mu}(D))^T \boldsymbol{\Sigma}(D)^{-1} (\mathbf{x} - \boldsymbol{\mu}(D)) + \ln|\boldsymbol{\Sigma}(D)| \right]$$

Key advantages:

- Uses the **full covariance structure** between channels
- Naturally handles **inter-channel correlations**
- Provides **principled uncertainty** from the probabilistic model
- Demonstrated **0.8% mean absolute error** (best published result)

## 3-Channel Mode

```python
from chromadose.methods import MultigaussianCalibration, MultigaussianSolver

# Build calibration from ROI pixel samples
mg_cal = MultigaussianCalibration(doses=doses, pixel_samples=samples)

solver = MultigaussianSolver(mg_cal)
dose_map = solver.solve(film, calibration)
```

## 6-Channel Mode (Pre-Irradiation)

When pre-irradiation scans are available, the response vector becomes `[R_pre, G_pre, B_pre, R_post, G_post, B_post]`:

```python
mg_cal = MultigaussianCalibration.from_film_rois(
    doses=doses, films=post_films, rois=rois, pre_films=pre_films,
)

solver = MultigaussianSolver(mg_cal)
dose_map = solver.solve_6channel(film, pre_film, calibration)
```

## Performance

- 550x500 image: **4.7s** (optimized from 133s via vectorized grid search + parabolic interpolation)
- Dense 200-point grid evaluation, all pixels processed simultaneously
- Uncertainty computed from NLL curvature at zero extra cost
