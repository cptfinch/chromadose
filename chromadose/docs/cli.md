# Command Line Interface

chromadose provides a CLI for the full dosimetry pipeline.

## Commands

### `chromadose calibrate`

Build calibration from scanned film strips.

```bash
chromadose calibrate \
  --films cal_0Gy.tif cal_1Gy.tif cal_2Gy.tif cal_4Gy.tif \
  --doses 0 1 2 4 \
  -o calibration.json
```

### `chromadose solve`

Convert a treatment film to a dose map.

```bash
chromadose solve \
  --film treatment.tif \
  --cal calibration.json \
  --method micke \
  -o dose.npy
```

Options:

- `--method`: `micke` (default) or `mayer`
- `--plot`: display the dose map

!!! note
    The Multigaussian and ANN methods need dedicated calibration objects
    (`MultigaussianCalibration` / `ANNCalibration`) rather than the
    rational-function fit stored in a calibration JSON, so they are available
    through the [Python API](api.md) rather than the CLI.

### `chromadose gamma`

Run gamma analysis between measured and reference dose.

```bash
chromadose gamma \
  --measured dose.npy \
  --reference tps_dose.npy \
  --criteria 3/3 \
  --threshold 10 \
  --pixel-size 0.353 \
  -o gamma.npy
```

### `chromadose report`

Generate a PDF QA report.

```bash
chromadose report \
  --measured dose.npy \
  --reference tps_dose.npy \
  --title "IMRT QA Report" \
  --patient "PATIENT001" \
  --plan "Head & Neck VMAT" \
  -o report.pdf
```

### `chromadose batch-qa`

Solve many treatment films with a shared calibration and, optionally,
gamma-compare each one against a single reference dose. Per-film dose maps,
gamma maps, and a `summary.csv` are written to the output directory.

```bash
chromadose batch-qa *.tif \
  --cal calibration.json \
  --ref tps_dose.dcm \
  --criteria 3/3 \
  --threshold 10 \
  --pixel-size 0.353 \
  --outdir batch_qa_out
```

Options:

- `--cal`: calibration JSON (required)
- `--method`: `micke` (default) or `mayer`
- `--ref`: shared reference dose, either a NumPy `.npy` array (already on the
  film grid) or a DICOM RT Dose file (resampled to the film grid, using the
  maximum-dose slice). Omit to solve without gamma analysis.
- `--criteria`, `--threshold`, `--pixel-size`: gamma parameters (as in
  `chromadose gamma`)
- `--outdir`: output directory (default `batch_qa_out`)

The command exits non-zero if any film fails to process, while still
completing the rest of the batch.

### `chromadose export-dicom`

Export a measured dose map back to a DICOM RT Dose file so it can be archived
or round-tripped into the treatment planning system. Dose is stored as
unsigned 32-bit integers with a `DoseGridScaling` factor (units Gy), matching
how a TPS exports RT Dose.

```bash
chromadose export-dicom \
  --dose dose.npy \
  --pixel-size 0.353 \
  --patient "PATIENT001" \
  --plan "Head & Neck VMAT" \
  -o dose.dcm
```

The written file round-trips through `chromadose.io.load_dicom_dose` (and any
DICOM-aware TPS). 2D dose maps are written as a single-frame export; 3D arrays
`(n_slices, H, W)` are written as a multi-frame dose volume. Requires the
`dicom` extra (`pip install chromadose[dicom]`).
