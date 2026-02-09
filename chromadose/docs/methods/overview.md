# Dosimetry Methods

chromadose implements four multichannel film dosimetry methods. All share the same calibration model — the rational function $\text{pixel}(D) = \frac{r + sD}{t + D}$ — but differ in how they combine information from multiple color channels to estimate dose.

## Comparison

| Method | Year | Approach | Speed | Best for |
|---|---|---|---|---|
| [Micke](micke.md) | 2011 | Least-squares multichannel | 0.14s | General use, original method |
| [Mayer](mayer.md) | 2012 | Analytical optimization | 0.04s | Speed-critical applications |
| [Multigaussian](multigaussian.md) | 2018 | Maximum likelihood (MLE) | 4.7s | Best accuracy, research |
| [ANN](ann.md) | 2025 | Neural network | ~1s | Batch-independent calibration |

*Times measured on a 550x500 pixel film image.*

## Unified API

All methods share the same interface:

```python
solver = SomeMethod()
dose_map = solver.solve(film, calibration)

# Every method returns:
dose_map.dose          # (H, W) dose in Gy
dose_map.uncertainty   # (H, W) per-pixel uncertainty
dose_map.dose_r        # (H, W) red channel dose
dose_map.dose_g        # (H, W) green channel dose
dose_map.dose_b        # (H, W) blue channel dose
dose_map.method        # "micke", "mayer", "multigaussian", or "ann"
```
