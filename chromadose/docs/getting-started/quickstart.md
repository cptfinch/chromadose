# Quick Start

## 1. Build Calibration

Scan your calibration film strips and extract mean pixel values at each known dose:

```python
import chromadose as cd

cal = cd.Calibration.from_arrays(
    doses=[0, 0.5, 1, 2, 4, 7, 9],       # Gy
    red_pixels=[0.221, 0.205, 0.190, ...],  # mean red at each dose
    green_pixels=[0.042, 0.041, 0.040, ...],
    blue_pixels=[0.067, 0.065, 0.063, ...],
)

# Save for reuse
cal.save("calibration.json")
```

Or load TIFF files directly:

```python
from chromadose.core.image import load_tiff

film = load_tiff("calibration_strip.tif")
```

## 2. Convert Film to Dose

```python
from chromadose.core.image import load_tiff
from chromadose.methods import MickeSolver

cal = cd.Calibration.load("calibration.json")
film = load_tiff("treatment_film.tif")

solver = MickeSolver()
dose_map = solver.solve(film, cal.result)

print(f"Max dose: {dose_map.dose.max():.2f} Gy")
print(f"Uncertainty: {dose_map.uncertainty.mean():.3f} Gy (mean)")
```

## 3. Try Different Methods

```python
from chromadose.methods import MayerSolver

mayer_result = MayerSolver().solve(film, cal.result)
```

## 4. Gamma Analysis

```python
from chromadose.analysis import gamma_2d

gamma = gamma_2d(
    reference=tps_dose,          # from TPS (DICOM or npy)
    evaluated=dose_map.dose,     # from film
    dose_criteria=3.0,           # 3%
    distance_criteria_mm=3.0,    # 3mm
    pixel_size_mm=film.pixel_size_mm,
)

print(f"Pass rate: {gamma.pass_rate * 100:.1f}%")
```

## 5. Generate Report

```python
from chromadose.io import generate_report

generate_report(
    "qa_report.pdf",
    dose_map,
    gamma_result=gamma,
    reference_dose=tps_dose,
    title="IMRT QA Report",
    patient_id="PATIENT001",
)
```

## 6. Command Line

```bash
chromadose calibrate --films cal*.tif --doses 0 0.5 1 2 4 7 9 -o cal.json
chromadose solve --film treatment.tif --cal cal.json --method micke -o dose.npy
chromadose gamma --measured dose.npy --reference tps.npy --criteria 3/3
chromadose report --measured dose.npy --reference tps.npy -o report.pdf
```
