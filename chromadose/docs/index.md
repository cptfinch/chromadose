# chromadose

**Modern multichannel radiochromic film dosimetry in Python.**

chromadose implements all major multichannel film dosimetry methods in one library, with built-in uncertainty estimation, gamma analysis, and PDF reporting.

## Why chromadose?

| Feature | chromadose | FilmQA Pro | OMG Dosimetry |
|---|:---:|:---:|:---:|
| Micke method | Yes | Yes | No |
| Mayer method | Yes | No | Yes |
| Multigaussian | Yes | No | No |
| Neural network | Yes | No | No |
| Uncertainty | Every method | Limited | No |
| Open source | MIT | Commercial | GPL |
| Vectorized | Yes | N/A | Row-by-row |

## Quick Example

```python
import chromadose as cd
from chromadose.methods import MickeSolver

# Load calibration and film
cal = cd.Calibration.load("calibration.json")
film = cd.FilmScan(red=red, green=green, blue=blue)

# Convert to dose
dose_map = MickeSolver().solve(film, cal.result)

# Gamma analysis
from chromadose.analysis import gamma_2d
gamma = gamma_2d(reference, dose_map.dose, dose_criteria=3, distance_criteria_mm=3)
print(f"Pass rate: {gamma.pass_rate * 100:.1f}%")
```

## Methods at a Glance

| Method | Speed (550x500) | Reference |
|---|---|---|
| **Mayer** | 0.04s | Mayer et al., Med. Phys. 2012 |
| **Micke** | 0.14s | Micke, Lewis, Yu, Med. Phys. 2011 |
| **Multigaussian** | 4.7s | Mendez et al., Phys. Med. Biol. 2018 |
| **ANN** | ~1s | Chang et al., Phys. Med. Biol. 2025 |
