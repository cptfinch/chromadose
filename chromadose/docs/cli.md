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

- `--method`: `micke` (default), `mayer`, or `multigaussian`
- `--plot`: display the dose map

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
