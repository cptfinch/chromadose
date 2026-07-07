# chromadose web backend

A small [FastAPI](https://fastapi.tiangolo.com/) service that exposes the
`chromadose` film-dosimetry library over HTTP, so a browser front-end (for
researchers and clinical physics departments) can drive the same pipeline the
CLI does. The heavy lifting (numpy/scipy/tifffile/pydicom) stays server-side;
the library and CLI are untouched.

> **RESEARCH USE ONLY — NOT A MEDICAL DEVICE.** See the chromadose `DISCLAIMER.md`.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health` | Liveness + chromadose version |
| POST | `/api/calibrate` | Build a calibration from calibration film TIFFs + doses |
| POST | `/api/solve` | Convert a film TIFF to a dose map (returns stats + PNG preview + `.npy`) |
| POST | `/api/gamma` | Gamma analysis between measured and reference `.npy` |
| POST | `/api/plan-geometry` | IEC 61217 beam geometry from a DICOM RT Plan |
| POST | `/api/export/rtdose` | Dose `.npy` → DICOM RT Dose download |
| POST | `/api/export/sr` | QA result → DICOM Structured Report download |
| POST | `/api/report` | Measured (± reference) → PDF QA report download |

Interactive docs are served at `/docs` (Swagger) and `/redoc` when running.

## Run locally

```bash
cd web/backend
uv sync --extra dev          # installs FastAPI + the sibling chromadose package
uv run uvicorn app.main:app --reload --port 8000
```

Then open <http://localhost:8000/docs>.

## Test

```bash
cd web/backend
uv run pytest -q
```

## Configuration

- `CHROMADOSE_CORS_ORIGINS` — comma-separated allowed origins (default `*` for
  local dev; set an explicit allow-list in production).

## Docker

```bash
docker build -f web/backend/Dockerfile -t chromadose-web .   # build from repo root
docker run -p 8000:8000 chromadose-web
```
