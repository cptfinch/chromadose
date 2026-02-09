# Open-Source Film Dosimetry: Code Analysis & Innovation Plan

## 1. OMG Dosimetry

**Repository:** [github.com/jfcabana/omg_dosimetry](https://github.com/jfcabana/omg_dosimetry)
**PyPI:** `pip install omg-dosimetry` (v1.8.1, July 2025)
**License:** MIT
**Stars:** 10 | **Forks:** 2 | **Contributors:** 3
**Last commit:** July 2025 (active — "CISSSO_Integration" merge)

### Who built it

- **Jean-François Cabana** — Clinical Medical Physicist, CISSS de Chaudière-Appalaches, Quebec, Canada (`jean-francois.cabana.cisssca@ssss.gouv.qc.ca`). Started the project in 2018.
- **Peter Truong** — CISSSO (Centre intégré de santé et de services sociaux de l'Outaouais), Quebec. Recent contributor focused on integration.
- **Luis Alfonso Olivares Jimenez** — Medical Physicist, UNAM (Mexico). Listed as maintainer. Also the author of Dosepy.

### Architecture (5,122 lines of Python)

```
src/omg_dosimetry/
├── calibration.py   (942 lines)   — LUT class: film detection, ROI extraction, calibration curves
├── tiff2dose.py     (727 lines)   — Gaf class: multichannel dose conversion (Mayer et al.)
├── analysis.py      (1571 lines)  — DoseAnalysis class: gamma analysis, TPS comparison, registration
├── imageRGB.py      (1250 lines)  — ArrayImage class: RGB TIFF loading, averaging, stacking
├── tools.py         (565 lines)   — Ruler, helper utilities
├── i_o.py           (66 lines)    — Demo file retrieval
└── __init__.py      (1 line)      — Exports LUT, Gaf
```

### How it works (the actual math)

**Calibration** (`calibration.py`):
- Rational function: `dose = -c + b/(pixel - a)` (note: this is the **inverse** form, mapping pixel value → dose directly)
- `scipy.optimize.curve_fit` with initial params `p0=[0.1, 200, 500]`
- Also supports UnivariateSpline fitting
- Computes derivative `d(dose)/d(pixel) = -b/(pixel - a)²` — needed for Mayer optimization
- Optional: per-pixel lateral correction (separate calibration curve at each scanner position)

**Film-to-dose** (`tiff2dose.py`):
- Implements **Mayer et al. (2012)** optimized multichannel method, equations 2, 6, 7, 9
- For each pixel row:
  1. Convert each channel (R, G, B) independently to dose using calibration curves → Dr, Dg, Db
  2. Get derivatives at each point → Ar, Ag, Ab
  3. Compute optimized dose: `D_opt = (D_ave - RS * sum(Dk*Ak)/sum(Ak)) / (1 - RS)` (eq. 6)
  4. Compute disturbance map: `delta = sum((D_opt - Dk)*Ak) / sum(Ak²)` (eq. 7)
  5. Compute residual error: `RE = sqrt(sum((Dk + Ak*delta - D_opt)²))` (eq. 2)
- Where `RS = sum(Ak)² / (sum(Ak²) * 3)` (eq. 9)

**Analysis** (`analysis.py`):
- Gamma analysis via `pymedphys` library
- Film registration using fiducial markers
- Profile comparisons, pass rate vs criteria curves
- PDF report generation via `pylinac`

### Dependencies

Heavy dependency chain:
- `pylinac ~= 3.7` (medical physics toolkit — brings in many sub-dependencies)
- `pymedphys ~= 0.39` (gamma analysis)
- `spyder ~= 5.3` (IDE — unusual to have as a dependency)
- Requires Python >= 3.7, < 3.11 (quite restrictive)

### Strengths
- Complete pipeline from scanned TIFF → calibrated dose → gamma analysis vs TPS
- Lateral scanner correction is well-implemented
- Automatic film detection is genuinely useful
- PDF report generation for clinical documentation
- Well-commented, heavily docstringed code
- Demo files and examples included

### Weaknesses
- Python version pinned to < 3.11 (outdated)
- Spyder as a hard dependency is odd
- Only implements Mayer et al. method — no Multigaussian, no ANN
- Row-by-row processing loop (not fully vectorized — slow on large films)
- The rational function form `dose = -c + b/(x-a)` differs from Micke's `pixel = (r+s*D)/(t+D)` — it's the algebraic inverse, but the parametrization is different and may affect fitting stability
- No batch-independent calibration
- No pre-irradiation scan support
- Heavy dependency footprint for what is essentially ~5k lines of math

---

## 2. Dosepy

**Repository:** [github.com/LuisOlivaresJ/Dosepy](https://github.com/LuisOlivaresJ/Dosepy)
**PyPI:** `pip install Dosepy` (v0.12.2)
**License:** MIT
**Stars:** 7 | **Forks:** 3 | **Contributors:** 2
**Last commit:** September 2025 (active — "eqd2" merge)

### Who built it

- **Luis Alfonso Olivares Jimenez** — MSc Medical Physics (UNAM, Mexico), BSc Physics (Universidad de Guadalajara). Also maintains OMG Dosimetry.

### Architecture (7,517 lines)

```
src/Dosepy/
├── calibration.py         (1241 lines)  — LUT calibration (adopted from OMG)
├── tiff2dose.py           (551 lines)   — Film-to-dose conversion
├── image.py               (1423 lines)  — Image handling
├── rtdose.py              (557 lines)   — DICOM RT dose import
├── i_o.py                 (182 lines)   — I/O utilities
├── app.py                 (31 lines)    — GUI entry point
├── app_components/        (8 files)     — PySide6 GUI widgets
├── app_controller/        (698 lines)   — MVC controller
├── app_model/             (66 lines)    — MVC model
├── config/                (210 lines)   — Settings/configuration
├── tools/                 (6 files)     — Gamma, functions, array utils
└── old/                   (829 lines)   — Legacy code
```

### Key differences from OMG

- Has a **desktop GUI** (PySide6)
- Requires Python >= 3.11 (modern)
- Uses `pydantic` for data validation
- More dependencies (simpleitk, plotly, gdown, etc.)
- Adopted OMG's LUT calibration class but extended it
- Has a proper test suite (`/tests/` directory + pytest + CI/CD)
- MVC architecture for the GUI
- Still under development toward medical device quality standards (IMDRF, NOM-241-SSA1-2021)
- Includes EQD2 (equivalent dose) calculations — going beyond pure film dosimetry

### Strengths
- Modern Python (3.11+)
- GUI for clinical users
- Testing infrastructure
- Active development with CI/CD
- Medical device quality aspirations

### Weaknesses
- Still v0.x (pre-release quality)
- Very heavy dependency list (simpleitk, plotly, gdown, etc.)
- Same mathematical method as OMG (Mayer et al.) — no Multigaussian
- GUI tied to PySide6 (Qt)

---

## 3. Comparison: Your Mathematica Notebook vs Open Source

| Aspect | Your notebook | OMG Dosimetry | Dosepy |
|---|---|---|---|
| **Math model** | Micke et al. `(r+s*D)/(t+D)` | Mayer et al. inverse rational | Same as OMG |
| **Optimization** | NMinimize sum of squared residuals across channels | Analytical eq. 6 (Mayer) — faster | Same as OMG |
| **Lateral correction** | No | Yes (per-pixel) | Yes |
| **Pre-irradiation scan** | No | No | No |
| **Multigaussian** | No | No | No |
| **Neural network** | No | No | No |
| **Gamma analysis** | No | Yes (pymedphys) | Yes |
| **Auto film detection** | No (manual ROI) | Yes | Yes |
| **Language** | Mathematica | Python | Python |

**Key insight:** All three implement essentially the same generation of method (Micke/Mayer, 2011-2012). Nobody in the open-source world has implemented the Multigaussian method (Mendez, 2018) or neural network calibration (Chang, 2021-2025).

---

## 4. Innovation Opportunities — Ranked by Impact

### Tier 1: Publishable research contributions

**1. Multigaussian method implementation (Python)**
- Mendez et al. demonstrated 0.8% mean absolute error — best published result
- Currently only available in commercial Radiochromic.com SaaS
- No open-source implementation exists anywhere
- Could be built as a module that plugs into OMG Dosimetry's architecture
- Paper potential: "Open-source implementation and validation of the Multigaussian method for multichannel radiochromic film dosimetry"

**2. Neural network batch-independent calibration**
- Dufek (2019): ANN eliminated batch-specific calibration, gamma > 97%
- Chang (2025): GANN adaptive calibration, ~2% uncertainty
- This is a genuine pain point — every new film lot needs fresh calibration
- Could train on accumulated calibration data across lots
- Paper potential: "Eliminating batch-specific calibration in radiochromic film dosimetry using neural networks"

**3. FLASH dosimetry validation toolkit**
- No standardized UHDR dosimetry protocol exists yet
- Film is THE primary dosimeter for FLASH
- A validated, open-source pipeline specifically for FLASH film dosimetry would be timely
- Paper potential: "An open-source toolkit for radiochromic film dosimetry in ultra-high dose-rate beams"

### Tier 2: Useful tools, community impact

**4. Port this project to Python as an OMG Dosimetry extension**
- Your Mathematica notebook implements the original Micke method
- Porting + adding Multigaussian would create a superset of existing tools
- Could contribute back to OMG Dosimetry as a PR

**5. EBT4-optimized models**
- EBT4 has different noise characteristics (46% better SNR)
- Existing calibration models were validated on EBT2/EBT3
- Optimized fitting for EBT4's improved response could extract additional accuracy

**6. Mobile phone scanning pipeline**
- Replace the expensive flatbed scanner requirement
- 2022 paper showed ANN can calibrate from phone photos
- Would dramatically lower the barrier to entry for film dosimetry

### Tier 3: Engineering improvements

**7. Vectorized processing**
- OMG Dosimetry processes row-by-row in a Python loop — slow
- Full numpy vectorization could speed up 10-100x
- Not publishable alone but improves usability

**8. Modern Python packaging**
- OMG requires Python < 3.11, has Spyder as dependency
- Cleaning up the dependency chain and supporting modern Python would help adoption

---

## 5. Suggested Plan

### Phase 1: Foundation (weeks 1-4)
- Get OMG Dosimetry running locally with your existing calibration films
- Reproduce your Mathematica results in Python using OMG
- Understand the Mayer et al. equations in the code vs Micke equations in your notebook
- Read the Mendez 2018 Multigaussian paper thoroughly

### Phase 2: Multigaussian Implementation (weeks 5-12)
- Implement the Multigaussian model as a new module
- Use your existing calibration data for initial testing
- Validate against published results from Mendez et al.
- Compare accuracy vs the existing Mayer method in OMG

### Phase 3: Validation & Publication (weeks 13-20)
- Acquire EBT4 film and new calibration data
- Run systematic comparison: Micke vs Mayer vs Multigaussian vs ANN
- Perform gamma analysis against TPS for clinical cases
- Write up results for Medical Physics or J. Appl. Clin. Med. Phys.

### Phase 4: Community Contribution
- Submit PR to OMG Dosimetry or release as standalone package
- Present at AAPM/COMP meeting
