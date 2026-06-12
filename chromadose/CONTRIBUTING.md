# Contributing to chromadose

Thanks for your interest in contributing! chromadose is open-source
research software for radiochromic film dosimetry. Contributions of
all sizes are welcome — bug fixes, new methods, documentation, tests,
example notebooks, and clinical validation data.

Before contributing, please read [DISCLAIMER.md](DISCLAIMER.md) — chromadose
is **not** a medical device and contributions should not introduce
clinical-use claims.

## Quick start

```bash
git clone https://github.com/cptfinch/chromadose
cd chromadose
uv sync                    # installs the project + dev deps
uv run pytest -q           # 92 tests should pass
uv run mypy src            # strict type checks
uv run ruff check          # lint
uv run mkdocs serve        # preview the docs site
```

Python 3.11+ is required.

## How to contribute

### Report a bug

Open a GitHub issue with:

- chromadose version (`python -c "import chromadose; print(chromadose.__version__)"`)
- Python version and OS
- Minimal reproducer (synthetic data preferred over real films)
- Expected vs observed behaviour
- For numerical bugs: which method, calibration setup, and ideally a
  reference value (paper, alternative tool, phantom measurement)

For potential security issues or numerical defects with downstream
safety implications, please follow [SECURITY.md](SECURITY.md) instead.

### Propose a change

For anything beyond a small fix, open an issue first to discuss the
approach. This avoids wasted work on changes that won't be merged.

Good first issues are labelled `good first issue` on GitHub.

### Submit a pull request

1. Fork and create a feature branch off `master`.
2. Make your change with tests covering the new behaviour.
3. Run the full check suite locally:
   ```bash
   uv run pytest -q
   uv run mypy src
   uv run ruff check
   uv run ruff format --check
   ```
4. Update docs under `docs/` if you've changed user-visible behaviour.
5. Add a CHANGELOG entry under `## [Unreleased]`.
6. Open a PR with a clear description of *what* and *why*.

### What we look for

- **Tests are mandatory.** New methods need tests covering accuracy
  against published reference values where possible. Bug fixes need a
  regression test.
- **Type hints everywhere.** mypy strict mode is enforced.
- **Vectorised numpy.** Per-pixel Python loops will be rejected unless
  there is no alternative — see existing methods for the pattern.
- **Minimal dependencies.** chromadose depends only on numpy, scipy,
  tifffile, matplotlib, and pydicom. Adding a new dependency requires
  strong justification.
- **Cite the literature.** If you implement a published method, add
  the reference in the docstring and the method's docs page.
- **No clinical claims.** Performance numbers must be qualified
  ("on synthetic data", "on the test phantom") and never imply
  clinical fitness for purpose.

## Areas where help is especially welcome

See the [GitHub Issues](https://github.com/cptfinch/chromadose/issues) and [milestones](https://github.com/cptfinch/chromadose/milestones) for the live roadmap. High-impact areas:

- **Clinical validation data** — anonymised IMRT/VMAT/SRS films vs
  TPS reference dose, for the validation publication (M3)
- **Pre-trained ANN weights** — for common scanner/film combinations
- **FLASH dose-rate correction** — for ultra-high dose rate research
- **DICOM RT Dose export** — round-tripping film dose back to TPS
- **Example notebooks** — real-world workflows for the docs site
- **Scanner-specific calibration recipes** — Epson, HP, Microtek, etc.

## Code of conduct

By participating, you agree to abide by the
[Code of Conduct](CODE_OF_CONDUCT.md). In short: be kind, assume good
faith, and remember this is research software maintained by volunteers.

## Licence

By contributing, you agree that your contributions will be licensed
under the [MIT Licence](LICENSE) — the same terms as the rest of the
project.
