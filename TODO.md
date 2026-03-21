# chromadose — TODO

## Current state

🟢 MVP → v1.0.0 released. Strong code quality, 4 methods, 92 tests. Primary gap is clinical validation and publication — without a peer-reviewed paper, clinical adoption is blocked.

**What exists (chromadose/src/chromadose/):**
- 4 multichannel dosimetry methods: Micke, Mayer, Multigaussian (MLE), ANN
- All fully vectorized (numpy) — Mayer 0.04s, Multigaussian 4.7s per 550x500 image
- 92 tests across all methods + gamma analysis + DICOM + calibration + CLI
- DICOM RT Dose import with automatic resampling to film grid
- PDF report generation
- CLI entry point (`chromadose`)
- Method comparison functionality
- 6-channel Multigaussian (pre-irradiation scan support)
- Modern Python 3.11+, mypy strict, ruff, minimal dependencies (numpy, scipy, tifffile, matplotlib)
- mkdocs documentation site with method guides + API docs
- MIT licence

**Key differentiator:** **First and only open-source implementation of the Mendez Multigaussian method.** Commercial equivalent: Radiochromic.com (cloud SaaS). Published best accuracy: 0.8% MAE.

## Best-in-class target (2026 research)

**Standards:** AAPM TG-235 (2019), IAEA TRS-398/469. Key journals: *Medical Physics*, *J. Appl. Clin. Med. Phys.*, *Physics in Medicine & Biology*.

**Competitive landscape:**
| Tool | Methods | Status |
|------|---------|--------|
| FilmQA Pro (Ashland) | Micke only | De facto clinical standard, $3-5k/licence |
| Radiochromic.com | Multigaussian | Cloud SaaS, proprietary |
| OMG Dosimetry | Mayer only | Open source, Python <3.11, heavy deps |
| Dosepy | Mayer | Open source, GUI-focused, pre-release |
| **chromadose** | Micke + Mayer + Multigaussian + ANN | Open source, release-ready |

**chromadose unique position:** Only tool with all 4 methods + open-source Multigaussian + principled uncertainty + modern Python + full test suite. Rivalling FilmQA Pro on science, surpassing it on accessibility and method breadth.

**What best-in-class still needs:**
1. Peer-reviewed publication (clinical adoption gate)
2. Clinical validation on 10-15 cases
3. PyPI publication (`pip install chromadose`)
4. Pre-trained ANN weights for common scanner/film configs
5. AAPM conference presence

## Gap analysis

| Area | Now | Target |
|------|-----|--------|
| Methods | ✅ All 4 implemented | + Pre-trained ANN weights, FLASH mode |
| Tests | ✅ 92 tests | + Clinical validation dataset |
| DICOM | ✅ RT Dose import | + RT Dose export, DICOM SR |
| Docs | ✅ mkdocs site | + Deploy live, example notebooks |
| Publication | ❌ None | Peer-reviewed paper in J. Appl. Clin. Med. Phys. |
| PyPI | ❌ Not published | `pip install chromadose` |
| Clinical validation | ❌ None | 10-15 IMRT/VMAT/SRS cases vs TPS |
| Pre-trained models | ❌ None | ANN weights for EBT3/EBT4 + common scanners |
| Community | ❌ None | GitHub stars, AAPM forum post, citation |

## Milestones

### M1 — Publish to PyPI (1 day — do this first)
- [ ] `uv build && uv publish` — pyproject.toml metadata already correct
- [ ] Verify: `pip install chromadose` works from clean environment
- [ ] Add PyPI badge to README
- [ ] Post to AAPM medical physics Slack/forum: "First open-source Multigaussian film dosimetry"

### M2 — Deploy documentation site (1 week)
- [ ] Deploy mkdocs-material site to GitHub Pages
- [ ] Add live examples (rendered Jupyter notebooks via nbconvert)
- [ ] Add installation + quick-start as first page
- [ ] Add method comparison page (Micke vs Mayer vs Multigaussian vs ANN — accuracy, speed, use cases)

### M3 — Clinical validation study (2-3 months)
- [ ] Acquire 10-15 IMRT/VMAT/SRS clinical QA films (EBT3 or EBT4)
- [ ] Compare all 4 methods against TPS reference dose (Eclipse or RayStation)
- [ ] Metrics: absolute dose error at central point, gamma analysis (3%/3mm), method agreement
- [ ] Sensitivity analysis: lateral correction on/off, pre-irradiation scan, ROI placement
- [ ] Document scanner commissioning procedure (lateral correction, linearity)
- [ ] This is the data for the publication

### M4 — Peer-reviewed publication
- [ ] Write manuscript: "chromadose: An open-source Python library for multichannel radiochromic film dosimetry including the first open-source Multigaussian implementation"
- [ ] Target journal: *Journal of Applied Clinical Medical Physics* (AAPM-affiliated, most relevant)
- [ ] Key claims to prove: (1) Multigaussian achieves <1% MAE in clinical setting, (2) all 4 methods in one open-source tool, (3) validated against clinical TPS data
- [ ] Submit AAPM Annual Meeting abstract (check current deadline)

### M5 — Pre-trained ANN weights
- [ ] Collect calibration films for 5-10 common scanner configurations (HP Scanjet G4010, Epson 10000XL, etc.)
- [ ] Train ANN per scanner/film configuration
- [ ] Package pre-trained weights into chromadose (download on first use)
- [ ] Reduces calibration burden — batch-independent out of the box

### M6 — Extend to FLASH dosimetry
- [ ] Implement FLASH-specific dose-rate correction (ultra-high dose rate > 40 Gy/s)
- [ ] Validate with FLASH beam data (requires clinical collaboration — PSI, Cincinnati, etc.)
- [ ] FLASH is the fastest-growing area in radiotherapy; positions chromadose as FLASH research standard

### M7 — Full clinical workflow
- [ ] DICOM RT Dose export (send film dose back to TPS for archival)
- [ ] DICOM Structured Report (SR) for formal QA documentation
- [ ] Batch processing CLI: `chromadose batch-qa *.tif --cal calibration.json --ref tps.dcm`
- [ ] IEC 61217 geometry metadata support (couch angles, gantry, collimator)

## Immediate next tasks

1. **Publish to PyPI** — single command, everything is ready
2. **Deploy mkdocs docs site** — GitHub Pages, one push
3. **Post announcement** — AAPM forum + medical physics Slack + LinkedIn
4. **Contact a proton therapy centre** (IBA connection is a direct in) — propose clinical validation collaboration
5. **Write the paper abstract** — stake the claim on open-source Multigaussian

## Notes

- The IBA proton therapy background is a direct path to clinical validation collaboration — proton QA is an ideal use case for Multigaussian accuracy
- OMG Dosimetry author (Cabana, Quebec) is a potential collaborator not competitor — different method focus
- EBT4 is becoming the new standard (46% better SNR, better lateral response) — worth validating against EBT4 specifically as part of the publication
- PyPI + validation paper are the two gates to clinical adoption — everything else follows
