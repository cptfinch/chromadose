# Film-to-TPS Registration

Spatially align a film measurement to a TPS dose distribution before gamma analysis.

## Automatic Registration

Optimizes translation and rotation to minimize dose differences:

```python
from chromadose.analysis import register_auto

result = register_auto(
    reference=tps_dose,
    evaluated=film_dose,
    pixel_size_mm=0.353,
    max_shift_mm=10.0,
    max_angle_deg=5.0,
)

print(f"Shift: dx={result.dx_mm:.1f}mm, dy={result.dy_mm:.1f}mm")
print(f"Rotation: {result.angle_deg:.2f} degrees")

# Use the registered image for gamma analysis
gamma = gamma_2d(tps_dose, result.registered, ...)
```

## Manual Registration

Apply a known shift and rotation:

```python
from chromadose.analysis import register_manual

result = register_manual(
    film_dose,
    dx_mm=2.5,
    dy_mm=-1.0,
    angle_deg=0.5,
    pixel_size_mm=0.353,
)
```

## How It Works

1. Uses `scipy.ndimage.map_coordinates` for bilinear interpolation
2. L-BFGS-B optimization of translation (x, y) and rotation (angle)
3. Cost function: mean squared dose difference in the above-threshold region
