# chromadose web app

A browser front-end over the `chromadose` film-dosimetry library, aimed at
researchers and clinical physics departments who want the pipeline without the
CLI. The library and CLI stay the source of truth; this is an additional surface.

```
web/
├── backend/     FastAPI service wrapping the chromadose Python package (implemented)
└── frontend/    Single-page UI (first pass, no build step), served by the backend at /
```

- **backend/** — HTTP API mapping 1:1 to the library functions (calibrate, solve,
  gamma, plan-geometry, export RT Dose / SR, PDF report). See `backend/README.md`.
- **frontend/** — a first-pass UI covering calibrate → dose → gamma → export, plus
  an RT Plan geometry tool. The backend serves it at `/`, so one process runs the
  whole app. See `frontend/README.md`. It stands in until the Claude Design mock
  is imported.

> **RESEARCH USE ONLY — NOT A MEDICAL DEVICE.** See the chromadose `DISCLAIMER.md`.
