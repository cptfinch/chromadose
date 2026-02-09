# Micke Method (2011)

!!! info "Reference"
    Micke A, Lewis DF, Yu X. "Multichannel film dosimetry with nonuniformity correction." *Med. Phys.* 2011;38(5):2523-34.

## Theory

The original multichannel method. For each pixel, find the dose $D$ that minimizes the sum of squared residuals across all color channels:

$$D^* = \arg\min_D \sum_{c \in \{R,G,B\}} \left[ \text{pixel}_c - \frac{r_c + s_c D}{t_c + D} \right]^2$$

## Implementation

chromadose uses **vectorized Gauss-Newton refinement** — not per-pixel `scipy.optimize`. This processes the entire image in ~10 Newton iterations, fully vectorized over all pixels simultaneously.

## Usage

```python
from chromadose.methods import MickeSolver

solver = MickeSolver()
dose_map = solver.solve(film, calibration)
```

## Performance

- 550x500 image: **0.14s**
- Uncertainty: from inter-channel disagreement (std of per-channel doses)
