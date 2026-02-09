# chromadose — Modern Multichannel Radiochromic Film Dosimetry

## Vision

A clean, modern Python library implementing **all major multichannel dosimetry methods** in one place:
Micke (2011), Mayer (2012), Multigaussian (Mendez 2018), and Neural Network (Chang 2025).

Designed for medical physicists who want accurate film dosimetry without vendor lock-in.

```python
import chromadose as cd

# Calibrate
cal = cd.Calibration.from_tiff("scans/calibration/", doses=[0, 0.5, 1, 2, 4, 7, 9])

# Convert film to dose — choose your method
dose = cd.FilmToDose("scans/treatment_film.tif", calibration=cal, method="multigaussian")

# Analyse against TPS
result = cd.GammaAnalysis(dose, reference="TPS_dose.dcm", criteria=(3, 3))
result.report()
```

---

## Name

**chromadose** — from "chromo" (color, as in radiochromic) + "dose"

Short, memorable, pip-installable, not taken on PyPI.

---

## Architecture

```
chromadose/
├── pyproject.toml
├── README.md
├── LICENSE                          (MIT)
├── docs/
│   ├── getting_started.md
│   ├── methods.md                   (mathematical background for each method)
│   ├── examples/
│   │   ├── basic_calibration.py
│   │   ├── multichannel_comparison.py
│   │   └── flash_dosimetry.py
│   └── api/                         (auto-generated from docstrings)
│
├── src/chromadose/
│   ├── __init__.py                  (public API: Calibration, FilmToDose, GammaAnalysis)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── image.py                 (TIFF loading, RGB separation, averaging, stacking)
│   │   ├── types.py                 (dataclasses: DoseMap, CalibrationData, FilmScan)
│   │   └── utils.py                 (lateral correction, scanner profile, pixel↔mm)
│   │
│   ├── calibration/
│   │   ├── __init__.py              (Calibration class — facade)
│   │   ├── roi.py                   (ROI detection — auto + manual)
│   │   ├── curves.py                (fit calibration curves per channel)
│   │   └── lut.py                   (lookup table generation, save/load, OMG-compatible I/O)
│   │
│   ├── methods/
│   │   ├── __init__.py              (registry: get_method("multigaussian") → solver)
│   │   ├── base.py                  (Protocol/ABC: DoseSolver interface)
│   │   ├── micke.py                 (Micke 2011 — numerical optimization per pixel)
│   │   ├── mayer.py                 (Mayer 2012 — analytical perturbation, eq. 6/7/9)
│   │   ├── multigaussian.py         (Mendez 2018 — multivariate Gaussian MLE)
│   │   └── ann.py                   (Neural network — batch-independent calibration)
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── gamma.py                 (2D gamma analysis — vectorized numpy)
│   │   ├── profiles.py              (line profiles, crossplane/inplane)
│   │   └── registration.py          (film↔TPS alignment via fiducials or optimization)
│   │
│   ├── io/
│   │   ├── __init__.py
│   │   ├── tiff.py                  (16-bit TIFF read/write)
│   │   ├── dicom.py                 (RT Dose DICOM import)
│   │   ├── omg_compat.py            (read/write OMG Dosimetry .pkl LUT files)
│   │   └── report.py                (PDF/HTML report generation)
│   │
│   └── cli.py                       (optional CLI: chromadose calibrate / convert / analyse)
│
└── tests/
    ├── conftest.py                  (shared fixtures: sample calibration data, test films)
    ├── test_calibration.py
    ├── test_micke.py
    ├── test_mayer.py
    ├── test_multigaussian.py
    ├── test_ann.py
    ├── test_gamma.py
    ├── test_io.py
    └── data/                        (small test TIFF files, reference doses)
```

---

## The Four Methods

### Method 1: Micke (2011) — `methods/micke.py`

The original. What your Mathematica notebook implements.

**Calibration model** (per channel k ∈ {R, G, B}):
```
pixel_k(D) = (r_k + s_k * D) / (t_k + D)
```

**Dose estimation** (per pixel):
```
D* = argmin_D  Σ_k [ pixel_k_observed - pixel_k(D) ]²
```

Solved numerically per pixel via `scipy.optimize.minimize_scalar`.

**Strengths:** Simple, intuitive, directly from the physics.
**Weaknesses:** Slow (numerical optimization per pixel), no analytical gradient info used.

### Method 2: Mayer (2012) — `methods/mayer.py`

What OMG Dosimetry implements. Analytical solution using linearized perturbation.

**Calibration model:** Same rational function, but inverted to get `D(pixel)` and its derivative `A_k = dD/d(pixel)` per channel.

**Dose estimation** (vectorized):
```
D_ave = (D_r + D_g + D_b) / 3
RS = [Σ A_k]² / (3 · Σ A_k²)                           # eq. 9
D_opt = (D_ave - RS · Σ(D_k · A_k) / Σ A_k) / (1 - RS) # eq. 6
delta = Σ((D_opt - D_k) · A_k) / Σ A_k²                 # eq. 7 (disturbance)
RE = √(Σ(D_k + A_k·delta - D_opt)²)                     # eq. 2 (residual)
```

**Strengths:** Fast (fully analytical, vectorizable), provides quality metrics (disturbance, residual).
**Weaknesses:** Linearization assumption, no probabilistic uncertainty model.

### Method 3: Multigaussian (Mendez 2018) — `methods/multigaussian.py`

The key innovation. No existing open-source implementation.

**Calibration model:**
For each calibration dose D_j, measure response vectors (pixel values across all channels, optionally including pre-irradiation scan). Estimate:
- Mean response vector: **μ**(D_j)
- Covariance matrix: **Σ**(D_j)

Interpolate **μ**(D) and **Σ**(D) as continuous functions of dose.

**Dose estimation** (per pixel):
Given observed response vector **x**, find dose D that maximizes the likelihood:
```
D* = argmax_D  f(x | μ(D), Σ(D))

    where f is the multivariate Gaussian PDF:
    f(x | μ, Σ) = (2π)^(-k/2) |Σ|^(-1/2) exp(-½ (x-μ)ᵀ Σ⁻¹ (x-μ))

    equivalently, minimize the Mahalanobis distance + log-determinant:
    D* = argmin_D  [ (x-μ(D))ᵀ Σ(D)⁻¹ (x-μ(D)) + ln|Σ(D)| ]
```

**Response vector options:**
- 3-channel: **x** = [R, G, B] from post-irradiation scan
- 6-channel: **x** = [R_pre, G_pre, B_pre, R_post, G_post, B_post] (with pre-irradiation scan)

The 6-channel version exploits correlation between pre- and post-irradiation responses to correct for film thickness variations — this is what gives the 0.8% accuracy.

**Implementation plan:**
```python
class MultigaussianSolver(DoseSolver):
    def calibrate(self, cal_data: CalibrationData):
        # For each dose level, compute mean vector and covariance matrix
        # from the calibration ROI pixel values
        self.mu = interpolate(doses, mean_vectors)    # vector-valued spline
        self.sigma = interpolate(doses, cov_matrices) # matrix-valued spline
        self.sigma_inv = precompute_inverses(self.sigma)

    def solve(self, pixels: np.ndarray) -> DoseMap:
        # For each pixel, minimize Mahalanobis distance + log|Σ|
        # Vectorized over image using broadcasting
        # Use scipy.optimize.minimize_scalar with bounded search
        pass
```

**Strengths:** Probabilistic, handles correlations, uses all available information, best published accuracy.
**Weaknesses:** Needs more calibration data points for covariance estimation, slightly slower than Mayer.

### Method 4: Neural Network (Chang 2021/2025) — `methods/ann.py`

**Calibration model:**
Train a neural network that maps pixel values → dose, learning the nonlinear relationship from calibration data. Can generalize across film batches.

**Architecture** (from Chang et al.):
- Input: [R, G, B] pixel values (optionally + scanner position for lateral correction)
- Hidden layers: 2-3 layers, 32-64 neurons each
- Output: dose (scalar)
- Loss: MSE against known calibration doses
- Framework: PyTorch (lightweight) or scikit-learn MLPRegressor (even lighter)

**Implementation plan:**
```python
class ANNSolver(DoseSolver):
    def calibrate(self, cal_data: CalibrationData):
        # Train small feedforward network on calibration pixel→dose pairs
        # Optionally load pre-trained weights for batch-independent mode
        pass

    def solve(self, pixels: np.ndarray) -> DoseMap:
        # Batch inference — very fast once trained
        pass
```

**Strengths:** Batch-independent calibration possible, fast inference, handles nonlinearities automatically.
**Weaknesses:** Requires more calibration data for training, "black box", needs validation.

---

## Core Design Principles

### 1. Method as a swappable strategy
```python
class DoseSolver(Protocol):
    def calibrate(self, cal_data: CalibrationData) -> None: ...
    def solve(self, pixels: np.ndarray) -> DoseMap: ...
    def uncertainty(self, pixels: np.ndarray) -> np.ndarray: ...
```

All methods implement the same interface. Users switch with one parameter.

### 2. Vectorized numpy throughout
No row-by-row Python loops. Everything operates on full arrays.
```python
# Bad (OMG Dosimetry style):
for i in range(ysize):
    row = img[i, :, :]
    dose_r[i, :] = ...

# Good:
dose_r = rational_inv(img[:, :, 0], *params_r)  # whole image at once
```

### 3. Minimal dependencies
```toml
[project]
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.24",
    "scipy>=1.10",
    "tifffile>=2023.1",        # TIFF I/O (lightweight, no PIL needed)
    "matplotlib>=3.7",         # plotting only
]

[project.optional-dependencies]
dicom = ["pydicom>=2.4"]       # only if reading RT Dose
ann = ["torch>=2.0"]           # only if using neural network method
report = ["jinja2>=3.1"]       # only if generating reports
cli = ["click>=8.0"]           # only if using CLI
```

4 required dependencies. Everything else optional.

### 4. Immutable data, pure functions where possible
```python
@dataclass(frozen=True)
class CalibrationData:
    doses: np.ndarray           # (n_doses,)
    pixel_values: np.ndarray    # (n_doses, n_rois, n_channels)
    pre_irrad: np.ndarray | None  # optional pre-irradiation values

@dataclass(frozen=True)
class DoseMap:
    dose: np.ndarray            # (height, width) in Gy
    uncertainty: np.ndarray     # (height, width) estimated uncertainty
    metadata: dict              # method used, calibration info, etc.
```

### 5. Uncertainty quantification built in
Every method provides uncertainty estimates — not just a dose map.
- Micke/Mayer: propagate calibration curve fit uncertainty
- Multigaussian: directly from the covariance model
- ANN: ensemble or dropout uncertainty

---

## Public API Design

### Calibration
```python
import chromadose as cd

# From scanned calibration films
cal = cd.Calibration.from_tiff(
    path="scans/calibration/",
    doses=[0, 0.5, 1, 2, 4, 7, 9],   # Gy
    lateral_correction=True,
    beam_profile="profile.txt",         # optional
)

# Save/load
cal.save("my_calibration.json")         # human-readable
cal = cd.Calibration.load("my_calibration.json")

# Import from OMG Dosimetry
cal = cd.Calibration.from_omg("Demo_calib.pkl")

# Inspect
cal.plot_curves()                       # show fitted curves per channel
cal.plot_residuals()                    # fitting quality
cal.summary()                           # print dose range, channels, fit params
```

### Film to Dose
```python
# Convert scanned film to dose
dose = cd.FilmToDose(
    film="scans/treatment.tif",
    calibration=cal,
    method="multigaussian",             # or "micke", "mayer", "ann"
    pre_irradiation="scans/pre.tif",    # optional, for Multigaussian 6-channel mode
)

# Access results
dose.dose          # DoseMap — the optimized dose array
dose.dose_r        # red channel dose
dose.dose_g        # green channel dose
dose.dose_b        # blue channel dose
dose.uncertainty   # per-pixel uncertainty estimate
dose.disturbance   # non-dose perturbation map (Mayer/Multigaussian)
dose.residual      # residual error map

# Compare methods
comparison = cd.compare_methods(
    film="scans/treatment.tif",
    calibration=cal,
    methods=["micke", "mayer", "multigaussian"],
)
comparison.plot()   # side-by-side dose maps and difference maps
comparison.table()  # statistical comparison
```

### Analysis
```python
# Gamma analysis vs TPS
gamma = cd.GammaAnalysis(
    film_dose=dose,
    reference="TPS_dose.dcm",          # DICOM RT Dose
    criteria=(3, 3),                     # 3%/3mm
    threshold=10,                        # ignore below 10% of max dose
)

gamma.pass_rate          # e.g., 98.5%
gamma.plot()             # gamma map
gamma.plot_histogram()   # gamma value distribution
gamma.plot_profiles()    # interactive crossplane/inplane profiles

# Generate report
cd.report(
    dose=dose,
    gamma=gamma,
    output="QA_report.pdf",
    author="Physics Department",
    notes="IMRT prostate plan verification",
)
```

### CLI
```bash
# Quick conversion
chromadose convert treatment.tif --cal my_cal.json --method multigaussian -o dose.tif

# Full QA pipeline
chromadose qa treatment.tif --cal my_cal.json --ref TPS_dose.dcm --gamma 3,3 --report report.pdf

# Compare methods
chromadose compare treatment.tif --cal my_cal.json --methods micke,mayer,multigaussian
```

---

## v1.0 Roadmap

### Milestone 1: Core foundation (v0.1) — DONE
- [x] Project scaffold: pyproject.toml, CI, linting, type checking
- [x] `core/image.py`: 16-bit TIFF loading, RGB separation, multi-scan averaging
- [x] `core/types.py`: CalibrationData, DoseMap, FilmScan dataclasses
- [x] `calibration/curves.py`: rational function fitting per channel
- [x] `methods/micke.py`: original Micke method (vectorized Newton refinement)
- [x] Tests: 22 passing
- [x] **Deliverable:** reproduced Mathematica results in Python

### Milestone 2: Mayer method + infrastructure (v0.2) — DONE
- [x] `methods/mayer.py`: analytical Mayer method (fully vectorized)
- [x] Cross-validate Micke vs Mayer on same data
- [x] **Deliverable:** feature parity with OMG Dosimetry core

### Milestone 3: Multigaussian method (v0.3) — DONE
- [x] `methods/multigaussian.py`: full implementation
  - [x] Calibration: mean vector + covariance matrix per dose level
  - [x] Interpolation of μ(D) and Σ(D)
  - [x] MLE dose estimation (Mahalanobis distance minimization)
  - [x] Uncertainty from the probabilistic model
- [x] Comparison: Micke vs Mayer vs Multigaussian on real Ashland data
- [x] 35 tests all passing
- [x] **Deliverable:** first open-source Multigaussian implementation

### Milestone 4: Analysis + reporting (v0.4) — DONE
- [x] `analysis/gamma.py`: vectorized 2D gamma analysis (Low 1998)
- [x] `analysis/profiles.py`: dose profiles with comparison metrics
- [x] `io/dicom.py`: DICOM RT Dose import with resampling
- [x] `io/report.py`: PDF report generation (dose maps, gamma, profiles)
- [x] 70 tests all passing
- [x] **Deliverable:** complete QA pipeline

### Milestone 5: Neural network + CLI (v0.5) — DONE
- [x] `methods/ann.py`: ANN dose solver with ensemble uncertainty (pure numpy/scipy)
- [x] `cli.py`: command-line interface (calibrate, solve, gamma, report)
- [x] CLI entry point in pyproject.toml
- [x] 82 tests all passing
- [x] **Deliverable:** ML-enhanced dosimetry

### Milestone 6: v1.0 release — DONE
- [x] Multigaussian 28x speedup (133s -> 4.7s): vectorized grid + parabolic interpolation
- [x] 6-channel Multigaussian with pre-irradiation scans (solve_6channel)
- [x] `analysis/registration.py`: automatic + manual film-to-TPS alignment
- [x] README with API docs, CLI usage, references
- [x] Version bumped to 1.0.0, PyPI-ready metadata
- [x] 92 tests, all passing
- [x] **Deliverable:** v1.0.0 ready for community release

### Future work
- [ ] Documentation site (mkdocs-material)
- [ ] PyPI publication
- [ ] Example Jupyter notebooks
- [ ] Pre-trained ANN weights for common EBT3/EBT4 scanner combos
- [ ] Validation paper + AAPM/COMP abstract

---

## Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Python version | >= 3.11 | Pattern matching, tomllib, modern typing |
| Array library | numpy | Universal, fast, no GPU needed for 2D images |
| Fitting | scipy.optimize | Proven, well-tested |
| TIFF I/O | tifffile | Lightweight, handles 16-bit correctly |
| Testing | pytest | Standard |
| Type checking | mypy (strict) | Catch bugs early, better IDE support |
| Linting | ruff | Fast, replaces flake8+isort+pyupgrade |
| Docs | mkdocs-material | Clean, searchable, auto-generated API docs |
| CI | GitHub Actions | pytest + mypy + ruff on every PR |
| Packaging | pyproject.toml (setuptools) | Standard, no setup.py needed |

---

## What makes this different from OMG Dosimetry

| Aspect | OMG Dosimetry | chromadose |
|---|---|---|
| Methods | Mayer only | Micke + Mayer + Multigaussian + ANN |
| Multigaussian | No | Yes (first open-source implementation) |
| Pre-irradiation scans | No | Yes (6-channel Multigaussian) |
| Neural network | No | Yes (batch-independent calibration) |
| Uncertainty | No | Built into every method |
| Processing | Row-by-row loops | Fully vectorized numpy |
| Python version | < 3.11 | >= 3.11 |
| Dependencies | pylinac, pymedphys, spyder | numpy, scipy, tifffile, matplotlib |
| Type hints | No | Yes (mypy strict) |
| Method comparison | No | Built-in `compare_methods()` |
| OMG compatibility | N/A | Can import OMG .pkl LUT files |
