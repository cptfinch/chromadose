# Radiochromic Film Dosimetry: Literature Review & State of the Art

## 1. Foundational Paper

The multichannel dosimetry method used in this project is based on:

> **Micke A, Lewis DF, Yu X.** "Multichannel film dosimetry with nonuniformity correction."
> *Medical Physics.* 2011;38(5):2523-2534.
> DOI: [10.1118/1.3576105](https://doi.org/10.1118/1.3576105)

This paper introduced the rational function model `(r + s*D) / (t + D)` fitted independently per RGB channel, with dose estimated by minimizing the sum of squared residuals across all channels. The method separates dose-dependent signal from non-dose-dependent artifacts (scanner nonuniformity, film thickness variations).

**Commercial implementation:** [FilmQA Pro](http://www.gafchromic.com/) by Ashland.

### Related foundational work

- **Mayer RR, Ma F, Chen Y, et al.** "Enhanced dosimetry procedures and assessment for EBT2 radiochromic film." *Medical Physics.* 2012;39(4):2147-55. DOI: [10.1118/1.3694100](https://doi.org/10.1118/1.3694100) — Introduced the "optimized multichannel" approach, comparing single-channel, dual-channel, and optimized multichannel methods. Together with Micke et al., this established what is known as the "Micke-Mayer method."

- **Mendez I, Peterlin P, Hudej R, et al.** "On multichannel film dosimetry with channel-independent perturbations." *Medical Physics.* 2014;41(1):011705. [arXiv:1401.1603](https://arxiv.org/abs/1401.1603) — Generalized the Micke-Mayer framework, showing both methods are special cases of a broader channel-independent perturbation model.

---

## 2. Evolution of Mathematical Models

### 2.1 Original: Rational Function (Micke et al., 2011)

```
PixelValue(D) = (r + s*D) / (t + D)
```

Fitted per channel. Dose estimated by minimizing multi-channel residual. Still widely used and implemented in FilmQA Pro.

### 2.2 Multigaussian Method (Mendez et al., 2018)

> **Mendez I, Polsak A, Hudej R, Casar B.** "The Multigaussian method: a new approach to multichannel radiochromic film dosimetry." 2018. [arXiv:1804.03885](https://arxiv.org/abs/1804.03885)

The main theoretical advance since Micke et al. Assumes the probability density function of the response vector (pixel values across all color channels, including pre- and post-irradiation scans) follows a **multivariate Gaussian distribution**. Achieved lower mean absolute errors (0.8-1.0%) compared to the Micke-Mayer method, especially when incorporating pre-irradiation scan data.

**Implemented in:** [Radiochromic.com](https://radiochromic.com) — a cloud-based SaaS platform for film dosimetry.

> **Mendez I, et al.** "A protocol for accurate radiochromic film dosimetry using Radiochromic.com." *Radiology and Oncology.* 2021;55(3):369-378. [PMC8366735](https://pmc.ncbi.nlm.nih.gov/articles/PMC8366735/)

### 2.3 Neural Network Approaches (2019-2025)

A growing but still niche area of research:

- **Dufek et al. (2019)** — "A trial for EBT3 film without batch-specific calibration using a neural network." Feed-forward ANN (PyTorch) to convert pixel values to dose without batch-specific calibration. Achieved gamma(3%/3mm) > 97% across different film batches. [PubMed:30625437](https://pubmed.ncbi.nlm.nih.gov/30625437/)

- **Chang et al. (2021)** — "Calibration of the EBT3 Gafchromic Film Using HNN Deep Learning." Hierarchical neural network using Keras to address the "aging effect" requiring quarterly recalibration. [PubMed:33628820](https://pubmed.ncbi.nlm.nih.gov/33628820/)

- **Chang et al. (2025)** — "Adaptive calibration of Gafchromic EBT3 film using generalized additive neural networks." *Scientific Reports.* 15(1):8208. The cutting edge: GANN method achieved dose differences within 5%, uncertainty ~2%, with improved stability over traditional recalibration. [Nature](https://www.nature.com/articles/s41598-025-92568-7)

- **ANN with mobile phone photos (2022)** — Neural network calibration of GafChromic XR-QA2 film using digital photos from a mobile device, bypassing flatbed scanners entirely. [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0969804322002044)

### 2.4 Model Selection Framework

> **Mendez I.** "Model selection for radiochromic film dosimetry." 2015. [arXiv:1505.00530](https://arxiv.org/abs/1505.00530)

Systematic comparison of fitting models for radiochromic film calibration curves.

---

## 3. Film Hardware Evolution

| Film Model | Year | Key Feature | Dose Range |
|---|---|---|---|
| EBT | 2004 | First self-developing EBT | 0.01-8 Gy |
| EBT2 | 2009 | Improved sensitivity | 0.01-10 Gy |
| EBT3 | 2011 | Symmetric design, silica particles (no Newton rings) | 0.2-10 Gy |
| EBT-XD | 2015 | Smaller nanocrystals, lower sensitivity for high-dose SRS/SBRT | 0.4-40 Gy |
| **EBT4** | **2022** | **Improved crystallite alignment** | **0.2-10 Gy** |

### EBT4 Key Improvements over EBT3

- **~46% better signal-to-noise ratio** (red and green channels at 500 cGy)
- **Reduced lateral response artifact** (3-8% improvement at 100mm off-center)
- **Better scanning orientation stability** (3.9% vs 6.8% OD difference)
- **Improved dose-response linearity**
- **Better agreement with TPS** in clinical verification (VMAT, SABR, HDR)

Key references:
- Palmer et al. (2023) — *Phys. Med. Biol.* [PubMed:37499683](https://pubmed.ncbi.nlm.nih.gov/37499683/)
- Miura et al. (2023) — *J. Appl. Clin. Med. Phys.* [PMC10402671](https://pmc.ncbi.nlm.nih.gov/articles/PMC10402671/)
- Akdeniz (2024) — *Radiation Physics and Chemistry* [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0969806X24002159)

**Manufacturer:** Ashland (Bridgewater, NJ) — still the manufacturer as of 2025. Originally developed by ISP (International Specialty Products), a division of GAF Chemical Corporation, acquired by Ashland in 2011.

---

## 4. Why Film Dosimetry Is Not a Fad

### The irreplaceable advantages

Film dosimetry is **not** replaceable by electronic detectors for several fundamental physics reasons:

**1. Sub-millimeter continuous 2D spatial resolution** — No electronic detector array comes close. Detector arrays have fixed spacing (typically >= 2.5mm) and interpolate between points. Film provides true continuous measurement. This is critical for:
  - Small field dosimetry (stereotactic radiosurgery fields as small as 4mm)
  - High dose-gradient regions where output factors can vary by 30% depending on detector choice
  - Commissioning new techniques

**2. Dose-rate independence up to ~10^12 Gy/s** — This is THE reason film is essential for FLASH radiotherapy. Active detectors (ionization chambers, diodes) **saturate** at ultra-high dose rates. Ion chambers have collection times of ~300 microseconds and experience severe ion recombination in FLASH regimes. Film integrates passively and doesn't care about dose rate.

**3. Near water-equivalence** — Tissue-equivalent response without the energy-dependent corrections needed for silicon-based detectors.

**4. Geometric flexibility** — Can be cut to any shape, placed inside phantoms, wrapped around curved surfaces, submerged in water. Electronic arrays are rigid.

**5. No angular dependence** — Unlike diodes and other solid-state detectors.

### The real limitations (honest assessment)

- **Passive / delayed readout** — Must wait 16-24 hours post-irradiation for polymerization to stabilize
- **Labor-intensive workflow** — Calibration, scanning, analysis pipeline is slow
- **Batch-to-batch variability** — Each film lot needs its own calibration
- **Single-use** — Cannot be re-used

### Where film is headed

Film dosimetry is shifting from routine daily QA (where electronic arrays are faster and good enough) toward **specialized, high-stakes applications** where nothing else works:
- FLASH radiotherapy beam characterization and dose verification
- Small field commissioning (SRS/SBRT)
- Dosimetry audits and inter-institutional comparisons
- Proton therapy end-of-range verification
- In-vivo dosimetry for total body irradiation

---

## 5. FLASH Radiotherapy: Film's Killer Application

FLASH radiotherapy delivers radiation at ultra-high dose rates (>= 40 Gy/s, up to 10^9 Gy/s) and has shown a remarkable "FLASH effect" — reduced normal tissue toxicity while maintaining tumor control. It is one of the most active areas in radiation oncology research.

**The dosimetry problem:** Conventional monitoring chambers saturate at UHDR. There are no validated standardized protocols for UHDR beam dosimetry yet. This creates a critical dependence on passive dosimeters, primarily radiochromic film.

Key references:
- Romano et al. (2022) — "Ultra-high dose rate dosimetry: Challenges and opportunities for FLASH radiation therapy." *Medical Physics.* [PMC9544810](https://pmc.ncbi.nlm.nih.gov/articles/PMC9544810/)
- Spruijt et al. (2025) — "Development of patient-specific pre-treatment verification procedure for FLASH proton therapy based on time resolved film dosimetry." *Medical Physics.* [Wiley](https://aapm.onlinelibrary.wiley.com/doi/10.1002/mp.17534)
- FLASH RT dosimeters review (2023) — [PMC10417829](https://pmc.ncbi.nlm.nih.gov/articles/PMC10417829/)

---

## 6. Software Landscape

### 6.1 Commercial

| Software | Developer | Method | Notes |
|---|---|---|---|
| **FilmQA Pro** | Ashland | Micke et al. multichannel | Industry standard, v5.0+, large user base |
| **Radiochromic.com** | Radiochromic S.L. (Spain) | Multigaussian (Mendez) | Cloud-based SaaS, newer method |
| **eFilmQA** | — | Triple-channel | Viable alternative to FilmQA Pro |
| **SNC Patient** | Sun Nuclear | — | Lacks some advanced features per 2024 comparison |

Buddhavarapu et al. (2024) compared FilmQA Pro, SNC Patient, and eFilmQA for SRS QA. FilmQA Pro and eFilmQA were preferred. [Wiley](https://aapm.onlinelibrary.wiley.com/doi/10.1002/acm2.14203)

### 6.2 Open Source

| Project | Author | Language | Features | Link |
|---|---|---|---|---|
| **OMG Dosimetry** | J.F. Cabana | Python | Full pipeline: calibration, multichannel film-to-dose (Mayer method), dose analysis with gamma, lateral correction | [GitHub](https://github.com/jfcabana/omg_dosimetry), [PyPI v1.7.1](https://pypi.org/project/omg-dosimetry/) |
| **Dosepy** | Luis Olivares | Python | Film dosimetry, LUT calibration (adopted from OMG), gamma analysis, lateral correction, GUI | [GitHub](https://github.com/LuisOlivaresJ/Dosepy), [Docs](https://dosepy.readthedocs.io) |
| **Film-Dosimetry** | Simon Biggs | Python | Earlier Python implementation | [GitHub](https://github.com/SimonBiggs/Film-Dosimetry) |
| **SlicerRT FilmDosimetry** | SlicerRT | Python/3D Slicer | 3D Slicer extension for film analysis | [GitHub](https://github.com/SlicerRt/FilmDosimetryAnalysis) |

**OMG Dosimetry** is the most comprehensive open-source option. It implements:
- Automatic film detection from scans
- Lateral scanner response correction (per-pixel calibration curves)
- Optimized multichannel dose conversion (Mayer et al. method)
- Quality metrics: disturbance maps, residual error, consistency maps
- Gamma analysis against TPS reference doses
- DICOM import for TPS dose comparison

**Dosepy** adopts OMG's calibration module and adds a GUI focused on film dosimetry. MIT licensed. Actively maintained.

Both are listed on [awesome-medphys](https://github.com/jrkerns/awesome-medphys).

---

## 7. Comprehensive Reviews

- **Darafsheh A. (2025)** — "A review on radiochromic film dosimetry in radiation therapy." *J. Appl. Clin. Med. Phys.* The most current comprehensive review. [Wiley](https://aapm.onlinelibrary.wiley.com/doi/full/10.1002/acm2.70365), [PMC12672139](https://pmc.ncbi.nlm.nih.gov/articles/PMC12672139/)

- **Devic S. (2011)** — "Radiochromic film dosimetry: past, present, and future." *Physica Medica.* [PubMed:21050785](https://pubmed.ncbi.nlm.nih.gov/21050785/)

- **Devic S, Tomic N, Lewis D. (2016)** — "Reference radiochromic film dosimetry: Review of technical aspects." *Physica Medica.* [PubMed:27020097](https://pubmed.ncbi.nlm.nih.gov/27020097/)

---

## 8. Innovation Opportunities

Gaps and potential research/development directions identified from this review:

### 8.1 Implement the Multigaussian method
No open-source implementation of Mendez's Multigaussian method exists. The existing open-source tools (OMG Dosimetry, Dosepy) implement the older Micke-Mayer approach. Building a Python implementation of the Multigaussian model would be a genuine contribution — it demonstrated 0.8% mean absolute error vs higher errors for the Micke method.

### 8.2 Neural network calibration
The Chang et al. (2025) GANN approach and the Dufek et al. (2019) batch-independent ANN are promising but not yet available as open-source tools. Integrating neural network calibration into an existing framework like OMG Dosimetry could eliminate the need for batch-specific recalibration — a major workflow pain point.

### 8.3 Mobile phone scanning
The 2022 paper on ANN calibration using mobile phone photos instead of flatbed scanners opens the possibility of a smartphone-based film dosimetry app. No production-quality implementation exists.

### 8.4 FLASH dosimetry protocols
With no standardized UHDR dosimetry protocols yet, there is an opportunity to contribute validated film-based protocols and reference datasets for the FLASH community.

### 8.5 Real-time / rapid readout
A 2019 paper in *Scientific Reports* ([Nature](https://www.nature.com/articles/s41598-019-41705-0)) explored real-time dosimetry with radiochromic films, potentially reducing the 24-hour wait time.

### 8.6 EBT4-specific calibration models
EBT4 has different crystallite alignment and noise characteristics than EBT3. Optimized fitting models specific to EBT4's improved response could extract better accuracy from the newer film.

### 8.7 Consolidate this project into a Python package
This Mathematica notebook implements the core Micke et al. algorithm. Porting it to Python and extending it with newer methods (Multigaussian, ANN calibration) could produce a competitive open-source tool, especially if combined with the best ideas from OMG Dosimetry and Dosepy.
