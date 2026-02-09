# Dose Profiles

Extract and compare 1D dose profiles from 2D dose maps.

## Extraction

```python
from chromadose.analysis import extract_row_profile, extract_col_profile, extract_line_profile

# Horizontal profile
profile = extract_row_profile(dose_map.dose, row=100, pixel_size_mm=0.353)

# Vertical profile
profile = extract_col_profile(dose_map.dose, col=150, pixel_size_mm=0.353)

# Arbitrary line
profile = extract_line_profile(
    dose_map.dose,
    start=(50, 20), end=(150, 180),  # (row, col) pixel coords
    n_points=200,
    pixel_size_mm=0.353,
)
```

## Comparison

```python
from chromadose.analysis import compare_profiles

comp = compare_profiles(reference=tps_profile, evaluated=film_profile)

print(f"Mean abs diff: {comp.mean_abs_diff_pct:.1f}%")
print(f"Max abs diff: {comp.max_abs_diff_pct:.1f}%")
```

`ProfileComparison` contains:

- `dose_diff` — absolute dose difference at each point
- `dose_diff_pct` — difference as % of reference max
- `mean_abs_diff_pct`, `max_abs_diff_pct` — summary metrics
