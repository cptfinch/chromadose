# Gamma Analysis

!!! info "Reference"
    Low DA, Harms WB, Mutic S, Purdy JA. "A technique for the quantitative evaluation of dose distributions." *Med. Phys.* 1998;25(5):656-61.

## Theory

The gamma index at each reference point is:

$$\gamma(\mathbf{r}_r) = \min_{\mathbf{r}_e} \sqrt{ \frac{|\mathbf{r}_r - \mathbf{r}_e|^2}{\Delta d_M^2} + \frac{(D_r - D_e)^2}{\Delta D^2} }$$

Where $\Delta d_M$ is the distance-to-agreement criterion (mm) and $\Delta D$ is the dose-difference criterion.

Points with $\gamma \leq 1$ **pass** the criteria.

## Usage

```python
from chromadose.analysis import gamma_2d

result = gamma_2d(
    reference=tps_dose,
    evaluated=film_dose,
    dose_criteria=3.0,           # 3%
    distance_criteria_mm=3.0,    # 3mm
    pixel_size_mm=0.353,         # e.g., 72 DPI film
    dose_threshold_pct=10.0,     # exclude < 10% of max
    dose_criteria_is_global=True,
)

print(f"Pass rate: {result.pass_rate * 100:.1f}%")
print(f"Points: {result.points_passed}/{result.points_evaluated}")
```

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `dose_criteria` | 3.0 | Dose difference criterion (%) |
| `distance_criteria_mm` | 3.0 | DTA criterion (mm) |
| `pixel_size_mm` | 1.0 | Pixel size in mm |
| `dose_threshold_pct` | 10.0 | Exclude below this % of max |
| `dose_criteria_is_global` | True | Global (max dose) or local (per-point) |
| `max_gamma` | 2.0 | Cap gamma values |

## Output

`GammaResult` contains:

- `gamma_map` — 2D gamma index array (NaN below threshold)
- `pass_rate` — fraction of points with $\gamma \leq 1$
- `criteria` — human-readable string, e.g. "3%/3mm global"
- `points_evaluated`, `points_passed` — counts
