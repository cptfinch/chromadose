# chromadose

Multichannel radiochromic film dosimetry for Gafchromic EBT film — the full
workflow from a flatbed scan to a calibrated dose map with uncertainty
quantification and gamma analysis. Python ≥3.11, MIT.

> ⚠️ **Research use only — not a medical device.** Any change that touches
> clinical use must preserve the disclaimer in `README.md`, `DISCLAIMER.md`, and
> the package docstring (it is load-bearing). Never claim medical-device status.

## Layout

The git root is `~/repos/chromadose`; the Python package lives **one level down**
at `chromadose/` (note the double-nesting — run dev commands from there).

```
chromadose/                 # package root — cd here for all dev commands
  src/chromadose/
    calibration/            # curve fitting (rational, polynomial)
    methods/                # micke, mayer, multigaussian, ann
    analysis/               # gamma, profiles, registration
    core/                   # image loading, types, utils
    io/                     # DICOM export, PDF reports
    cli.py
  tests/                    # pytest
  docs/                     # mkdocs-material site
  pyproject.toml, uv.lock
TODO.md                     # historical roadmap snapshot — live roadmap is in GitHub Issues
CHROMADOSE_DESIGN.md        # architecture
LITERATURE_REVIEW.md        # film dosimetry literature survey
OPEN_SOURCE_ANALYSIS.md     # competitive landscape
flake.nix / flake.lock      # nix dev shell
```

## Methods

Micke (Micke et al. 2011), Mayer, Multigaussian (Mendez — the open-source
differentiator), ANN (optional torch backend). **All methods must be fully
vectorized — per-pixel loops are a blocker.**

## Develop

From `~/repos/chromadose/chromadose/` (or `nix develop` from the root first):

```bash
uv sync --all-extras
uv run pytest                  # tests
uv run ruff check src/         # lint
uv run mypy src/chromadose/    # typecheck (strict)
uv run mkdocs serve            # docs preview at http://127.0.0.1:8000
```

CLI (installed entry point):

```bash
uv run chromadose calibrate <tiff> --doses <csv> [--method micke]
uv run chromadose analyze   <tiff> --calibration <cal> [--method micke]
uv run chromadose gamma     <ref>  <eval> [--criteria 3,3]
```

## Conventions

- Minimal runtime deps: numpy, scipy, tifffile, matplotlib. Optional extras:
  `[dicom]` (pydicom), `[ann]` (torch).
- New methods land in `src/chromadose/methods/` with a matching test file under
  `tests/`.
- ruff-formatted, mypy strict.

## Release

1. `CHANGELOG.md` — move Unreleased → new version, add date
2. Bump version in `pyproject.toml`
3. `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
4. `uv build && uv publish`   (needs `UV_PUBLISH_TOKEN`)
5. `git push origin vX.Y.Z`
6. GitHub Release with changelog excerpt

Current release: **v0.9.1** (PyPI + GitHub Releases, 2026-04-11). v1.0.0 is
gated on clinical validation + a peer-reviewed paper.

## Roadmap

Tracked in **GitHub Issues** — `gh issue list -R cptfinch/chromadose`. `TODO.md`
is a historical snapshot, not the source of truth.

## References

AAPM TG-235 (2019); Micke et al. (2011); Mendez et al. (Multigaussian);
IAEA TRS-398/469.

@CLAUDE.local.md
