# API Reference

## Core Types

### `FilmScan`
Scanned film with RGB channels normalized to [0, 1].

```python
from chromadose.core.types import FilmScan

film = FilmScan(red=red_array, green=green_array, blue=blue_array, dpi=72.0)
film.shape        # (H, W)
film.rgb          # (H, W, 3)
film.pixel_size_mm  # 25.4 / dpi
```

### `DoseMap`
Result of film-to-dose conversion.

```python
dose_map.dose          # (H, W) dose in Gy
dose_map.uncertainty   # (H, W) per-pixel uncertainty
dose_map.dose_r        # (H, W) red channel dose
dose_map.dose_g        # (H, W) green channel dose
dose_map.dose_b        # (H, W) blue channel dose
dose_map.method        # str
dose_map.metadata      # dict
```

### `Calibration`
Facade for building and managing calibrations.

```python
import chromadose as cd

cal = cd.Calibration.from_arrays(doses, red_pixels, green_pixels, blue_pixels)
cal.save("cal.json")
cal = cd.Calibration.load("cal.json")
cal.result    # CalibrationResult with .red, .green, .blue FitParams
cal.summary() # Human-readable summary string
cal.plot_curves()  # matplotlib figure
```

### `FitParams`
Rational function parameters for one channel: `pixel(D) = (r + sD) / (t + D)`

```python
params.pixel(dose_array)       # predict pixel values
params.dose(pixel_array)       # invert to dose
params.dpixel_ddose(dose_array)  # derivative
```

## Methods

### `MickeSolver`
```python
from chromadose.methods import MickeSolver
dose_map = MickeSolver().solve(film, calibration_result)
```

### `MayerSolver`
```python
from chromadose.methods import MayerSolver
dose_map = MayerSolver().solve(film, calibration_result)
```

### `MultigaussianSolver`
```python
from chromadose.methods import MultigaussianCalibration, MultigaussianSolver

mg_cal = MultigaussianCalibration(doses, pixel_samples)
solver = MultigaussianSolver(mg_cal)
dose_map = solver.solve(film, calibration_result)
dose_map = solver.solve_6channel(film, pre_film, calibration_result)
```

### `ANNSolver`
```python
from chromadose.methods import ANNCalibration, ANNSolver

ann_cal = ANNCalibration(n_hidden=32, n_ensemble=5)
ann_cal.fit(pixels, doses)
solver = ANNSolver(ann_cal)
dose_map = solver.solve(film, calibration_result)
```

## Analysis

### `gamma_2d()`
```python
from chromadose.analysis import gamma_2d
result = gamma_2d(reference, evaluated, dose_criteria=3.0, distance_criteria_mm=3.0)
result.pass_rate       # float [0, 1]
result.gamma_map       # (H, W) array
```

### Profile Functions
```python
from chromadose.analysis import extract_row_profile, compare_profiles
profile = extract_row_profile(dose, row=100, pixel_size_mm=1.0)
comp = compare_profiles(ref_profile, eval_profile)
```

### Registration
```python
from chromadose.analysis import register_auto, register_manual
result = register_auto(reference, evaluated, pixel_size_mm=1.0)
result.registered  # aligned dose map
```

## I/O

### DICOM Import
```python
from chromadose.io.dicom import load_dicom_dose, resample_to_film
rt_dose = load_dicom_dose("rtdose.dcm")
resampled = resample_to_film(rt_dose, film_shape=(500, 500), film_pixel_size_mm=0.353)
```

### PDF Reports
```python
from chromadose.io import generate_report
generate_report("report.pdf", dose_map, gamma_result=gamma, profiles=[comp])
```

## Image Loading
```python
from chromadose.core.image import load_tiff, load_tiff_averaged
film = load_tiff("scan.tif")
film = load_tiff_averaged(["scan1.tif", "scan2.tif", "scan3.tif"])
```
