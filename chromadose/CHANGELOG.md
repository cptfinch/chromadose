# Changelog

All notable changes to chromadose will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `DISCLAIMER.md` — research-use-only / not-a-medical-device statement
- `SECURITY.md` — vulnerability and numerical-defect reporting policy
- `CONTRIBUTING.md` — contributor guide
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1
- `CHANGELOG.md` — this file
- README disclaimer banner linking to DISCLAIMER.md
- Module docstring disclaimer in `chromadose/__init__.py`

## [1.0.0] — 2026

### Added
- Initial public release
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
