# Changelog

All notable changes to chromadose will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `chromadose batch-qa` CLI command: solve many films with a shared
  calibration and optionally gamma-compare each against a single reference
  (`.npy` or DICOM RT Dose), writing per-film dose/gamma maps and a
  `summary.csv`
- DICOM RT Dose **export**: `chromadose.io.save_dicom_dose` writes a measured
  dose map (2D or 3D, in Gy) to a valid RT Dose file that round-trips through
  `load_dicom_dose` and DICOM-aware treatment planning systems. Dose is stored
  as uint32 with a `DoseGridScaling` factor, as TPS systems do.
- `chromadose export-dicom` CLI command wrapping `save_dicom_dose`
- DICOM Structured Report (SR) export for QA documentation:
  `chromadose.io.save_dicom_sr` writes a Comprehensive SR documenting the
  dosimetry method, gamma analysis (criteria, pass rate, points
  evaluated/passed, dose threshold) and dose statistics as coded content items.
  `chromadose.io.read_dicom_sr` reads the document back into a flat dict.
- `chromadose export-sr` CLI command wrapping `save_dicom_sr` (computes the
  gamma section from `--measured` / `--reference`)
- IEC 61217 beam geometry support: a `BeamGeometry` type
  (`chromadose.BeamGeometry`) holding gantry / collimator / couch angles (plus
  beam name/number, energy, SSD) in the IEC 61217 convention, with range
  validation.
- `chromadose.io.load_beam_geometry` reads beam geometry from a DICOM RT Plan
  (first control point of each beam; treatment beams only by default).
- `chromadose plan-geometry` CLI command listing an RT Plan's beam angles.

### Fixed
- `chromadose --version` reported a hard-coded `1.0.0`; it now reports the
  installed package version (`chromadose.__version__`)
- `chromadose solve --method multigaussian` was advertised in the CLI help
  and docs but raised `ValueError` (the file-based CLI has no Multigaussian
  calibration object). The `solve` method choices are now restricted to the
  methods the CLI actually supports (`micke`, `mayer`), and the docs point to
  the Python API for Multigaussian/ANN

## [0.9.1] — 2026-04-11

Polish release. No new features — tightens the type-checking gate, cleans up
PyPI metadata, and adds CI coverage for mypy.

### Added
- `Documentation` URL in PyPI metadata pointing at the live mkdocs site
- mypy strict type-check step in the CI workflow (runs on Python 3.11/3.12/3.13)
- mypy overrides for scipy, matplotlib, tifffile, and pydicom (treated as
  untyped to avoid missing-stub noise)

### Changed
- `warn_return_any` disabled globally: numpy's typing surface returns `Any`
  from most array operations, which fights with strict mode on every
  function that returns an `NDArray`
- `chromadose.calibration.Calibration.plot_curves` now imports `Axes` and
  `Figure` from `matplotlib.axes` / `matplotlib.figure` directly, rather
  than relying on the runtime `plt.Axes` / `plt.Figure` aliases
- `tight_layout(rect=[...])` calls in `io/report.py` use tuple literals
  to match the typed signature

### Fixed
- `core.image._extract_dpi` now narrows `tif.pages[0]` to `TiffPage` via
  isinstance — `TiffFrame` doesn't carry `.tags`
- `methods.ann` casts `rng.integers(...)` to `int` before passing as seed;
  `NDArray` annotations in the L-BFGS-B inner closure now specify the
  element type
- `analysis.registration.cost` annotates its `params` argument with the
  numpy element type

## [0.9.0] — 2026-04-11

First public release on PyPI. Version `0.9.0` is a release candidate for
`1.0.0`; the major bump is reserved for the peer-reviewed publication and
clinical validation study.

### Added
- Initial public release
- `DISCLAIMER.md` — research-use-only / not-a-medical-device statement
- `SECURITY.md` — vulnerability and numerical-defect reporting policy
- `CONTRIBUTING.md` — contributor guide
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1
- `CHANGELOG.md` — this file
- README disclaimer banner linking to DISCLAIMER.md
- Module docstring disclaimer in `chromadose/__init__.py`
- Four multichannel film dosimetry methods:
  - **Micke** (Micke, Lewis, Yu 2011) — Newton refinement
  - **Mayer** (Mayer et al. 2012) — analytical optimisation with disturbance correction
  - **Multigaussian** (Mendez et al. 2018) — MLE on multivariate Gaussian, first open-source implementation
  - **ANN** (Chang et al. 2025) — neural network with ensemble uncertainty
- 6-channel Multigaussian variant with pre-irradiation scan support
- Calibration framework with red/green/blue channel fitting
- Gamma analysis (configurable dose/distance criteria)
- Image registration and dose profile extraction
- DICOM RT Dose import with automatic resampling to film grid
- PDF report generation
- CLI entry point (`chromadose`)
- Method comparison utility
- mkdocs-material documentation site with method guides and API reference
- 92 tests across all methods, calibration, gamma, DICOM, profiles, registration, CLI, and reports
- mypy strict type checking, ruff linting and formatting
- Modern Python 3.11+ with minimal dependencies (numpy, scipy, tifffile, matplotlib, pydicom)
- MIT licence
