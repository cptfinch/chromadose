# chromadose

Modern multichannel radiochromic film dosimetry in Python.

**chromadose** implements all major multichannel film dosimetry methods in one library, with built-in uncertainty estimation, gamma analysis, and PDF reporting.

## Methods

| Method | Reference | Description |
|---|---|---|
| **Micke** | Micke, Lewis, Yu (2011) | Original multichannel method — Newton refinement |
| **Mayer** | Mayer et al. (2012) | Analytical optimization with disturbance correction |
| **Multigaussian** | Mendez et al. (2018) | MLE on multivariate Gaussian N(mu(D), Sigma(D)) |
| **ANN** | Chang et al. (2025) | Neural network with ensemble uncertainty |

The Multigaussian implementation is the **first open-source** version of this method.

## Quick Start

```python
import chromadose as cd
from chromadose.core.image import load_tiff
from chromadose.methods import MickeSolver

# Load and calibrate
film = load_tiff("treatment_film.tif")
cal = cd.Calibration.from_arrays(
    doses=[0, 0.5, 1, 2, 4, 7, 9],
    red_pixels=red_means,
    green_pixels=green_means,
    blue_pixels=blue_means,
)

# Convert to dose
solver = MickeSolver()
dose_map = solver.solve(film, cal.result)
print(f"Max dose: {dose_map.dose.max():.2f} Gy")
```

## Gamma Analysis

```python
from chromadose.analysis import gamma_2d

result = gamma_2d(
    reference=tps_dose,
    evaluated=dose_map.dose,
    dose_criteria=3.0,        # 3%
    distance_criteria_mm=3.0, # 3mm
)
print(f"Pass rate: {result.pass_rate * 100:.1f}%")
```

## PDF Reports

```python
from chromadose.io import generate_report

generate_report(
    "qa_report.pdf",
    dose_map,
    gamma_result=result,
    title="IMRT QA Report",
    patient_id="PATIENT001",
)
```

## CLI

```bash
chromadose calibrate --films cal*.tif --doses 0 0.5 1 2 4 7 9 -o cal.json
chromadose solve --film treatment.tif --cal cal.json --method micke -o dose.npy
chromadose gamma --measured dose.npy --reference tps.npy --criteria 3/3
chromadose report --measured dose.npy --reference tps.npy -o report.pdf
```

## Installation

```bash
pip install chromadose
```

Optional extras:
```bash
pip install chromadose[dicom]    # DICOM RT Dose import
pip install chromadose[ann-gpu]  # PyTorch GPU acceleration for ANN
pip install chromadose[dev]      # Development tools
```

## Features

- **4 dosimetry methods** with a unified API
- **Uncertainty estimation** built into every method
- **2D gamma analysis** (Low 1998) with global/local dose criteria
- **Dose profiles** — row, column, or arbitrary line extraction
- **Film-to-TPS registration** — automatic or manual rigid alignment
- **DICOM RT Dose import** with resampling to film grid
- **PDF QA reports** — dose maps, gamma, profiles in one document
- **CLI** — full pipeline from command line
- **6-channel Multigaussian** — uses pre-irradiation scans for improved accuracy
- **Fully vectorized** — no per-pixel Python loops
- **Pure Python** — numpy + scipy only (torch optional for GPU)

## Performance

| Method | 550x500 image | Notes |
|---|---|---|
| Mayer | 0.04s | Analytical — fastest |
| Micke | 0.14s | Newton refinement |
| Multigaussian | 4.7s | Dense grid + parabolic interpolation |
| ANN | ~1s | Depends on ensemble size |

## Requirements

- Python >= 3.11
- numpy >= 1.24
- scipy >= 1.10
- tifffile >= 2023.1
- matplotlib >= 3.7

## References

1. Micke A, Lewis DF, Yu X. "Multichannel film dosimetry with nonuniformity correction." *Med. Phys.* 2011;38(5):2523-34.
2. Mayer RR, et al. "An improved dose response function for multichannel film dosimetry." *Med. Phys.* 2012;39(12):7596-602.
3. Mendez I, Polsak A, Hudej R, Casar B. "The Multigaussian method: a new approach to mitigating spatial heterogeneities with multichannel radiochromic film dosimetry." *Phys. Med. Biol.* 2018;63(17):175013.
4. Chang L-Y, et al. "GANN: a generalized artificial neural network for multichannel radiochromic film dosimetry." *Phys. Med. Biol.* 2025.
5. Low DA, et al. "A technique for the quantitative evaluation of dose distributions." *Med. Phys.* 1998;25(5):656-61.

## License

MIT
