# chromadose web app

A browser front-end over the `chromadose` film-dosimetry library, aimed at
researchers and clinical physics departments who want the pipeline without the
CLI. The library and CLI stay the source of truth; this is an additional surface.

```
web/
├── backend/     FastAPI service wrapping the chromadose Python package (implemented)
└── frontend/    Single-page UI — the imported Chromadose Web App design (pending)
```

- **backend/** — HTTP API mapping 1:1 to the library functions (calibrate, solve,
  gamma, plan-geometry, export RT Dose / SR, PDF report). See `backend/README.md`.
- **frontend/** — will hold the imported *Chromadose Web App* design, wired to the
  backend API.

> **RESEARCH USE ONLY — NOT A MEDICAL DEVICE.** See the chromadose `DISCLAIMER.md`.
