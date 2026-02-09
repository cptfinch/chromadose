# Mayer Method (2012)

!!! info "Reference"
    Mayer RR, et al. "An improved dose response function for multichannel film dosimetry." *Med. Phys.* 2012;39(12):7596-602.

## Theory

An analytical solution that avoids iterative optimization. Uses the derivatives of the calibration curves to compute an optimally-weighted dose from the per-channel estimates.

**Equation 6 (optimized dose):**

$$D_{\text{opt}} = \frac{\sum_c w_c D_c}{\sum_c w_c}$$

where $w_c = \left(\frac{dD_c}{d\text{pixel}_c}\right)^{-2}$ is the inverse-variance weight from equation 7.

The method also provides a **disturbance map** (equation 2) and **residual error** (equation 9) for quality metrics.

## Usage

```python
from chromadose.methods import MayerSolver

solver = MayerSolver()
dose_map = solver.solve(film, calibration)

# Mayer-specific metadata
disturbance = dose_map.metadata["disturbance"]
residual = dose_map.metadata["residual_error"]
```

## Performance

- 550x500 image: **0.04s** (fastest method)
- Fully analytical — no iterations needed
