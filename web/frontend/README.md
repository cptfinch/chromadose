# chromadose web UI (first pass)

A dependency-free single-page app over the backend API in `../backend`. There
is no build step: plain HTML, CSS and one classic script, so it can be served
as static files and edited directly.

```
index.html   the four workflow steps + the RT Plan geometry tool
styles.css   light/dark themes, responsive down to phone width, system fonts only
app.js       state, API calls, rendering (no framework, no external requests)
```

## Workflow

1. **Calibrate**: drop calibration film TIFFs, confirm each film's dose (guessed from
   filenames like `cal_2Gy.tif`), and fit the response curves. Or load a saved
   `calibration.json`. Shows the fitted curves and parameters.
2. **Calculate dose**: upload the treatment film, pick a method, get a dose map.
3. **Compare**: gamma analysis against a reference `.npy` (criteria, threshold, pixel size).
4. **Export & report**: DICOM RT Dose, DICOM Structured Report, or a PDF QA report.
5. **Tool: RT Plan geometry**: IEC 61217 beam angles from a DICOM RT Plan.

## Run it

The backend serves this directory at `/`, so one process runs the whole app:

```bash
cd web/backend
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
# open http://localhost:8000
```

Set `CHROMADOSE_FRONTEND_DIR` to serve a different directory (the Docker image does).

## Design notes

- **Nothing is persisted in the browser.** State is in memory only; exports can
  carry patient identifiers, so there is no `localStorage` or cookie use.
- **Steps are deep-linkable** (`/#compare`) and Back/Forward move between them.
- **Untrusted text is never inserted as HTML.** File names and RT Plan beam names
  go through `textContent`.
- The references and measured dose are exchanged as NumPy `.npy` files, because
  that is what the API takes. Reading a DICOM RT Dose as the reference is a
  CLI/library feature for now (`chromadose batch-qa --ref plan.dcm`).

## Known gaps

- The export endpoints do not yet accept an RT Plan, so beam geometry is not
  stamped into the exports from the web UI (it is available through the
  library and CLI).
- Only the file-based methods (`micke`, `mayer`) are exposed, as in the CLI.
- This is a first pass to prove the flow end to end; it is not the final design.
