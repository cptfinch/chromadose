"""Command-line interface for chromadose.

Usage:
    chromadose calibrate --films cal1.tif cal2.tif --doses 0 0.5 1 2 4 7 -o cal.json
    chromadose solve --film treatment.tif --cal cal.json --method micke -o dose.npy
    chromadose gamma --measured dose.npy --reference tps_dose.npy --criteria 3/3
    chromadose report --measured dose.npy --gamma gamma.npz -o report.pdf
    chromadose batch-qa *.tif --cal cal.json --ref tps.dcm --criteria 3/3
    chromadose export-dicom --dose dose.npy --pixel-size 0.353 -o dose.dcm
    chromadose export-sr --measured dose.npy --reference tps.npy -o qa_sr.dcm
    chromadose plan-geometry --plan rtplan.dcm

Uses argparse (stdlib) to avoid extra dependencies.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from chromadose import __version__

if TYPE_CHECKING:
    from chromadose.core.types import BeamGeometry
    from chromadose.io.dicom import RTDose

# Methods wired into the simple file-based CLI. Multigaussian and ANN require
# dedicated calibration objects (MultigaussianCalibration / ANNCalibration)
# rather than the rational-function fit stored in a calibration JSON, so they
# are only available through the Python API, not the CLI.
_CLI_METHODS = ["micke", "mayer"]


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="chromadose",
        description="Modern multichannel radiochromic film dosimetry",
    )
    parser.add_argument(
        "--version", action="version", version=f"chromadose {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- calibrate ---
    cal_parser = subparsers.add_parser("calibrate", help="Build calibration from film scans")
    cal_parser.add_argument("--films", nargs="+", required=True, help="TIFF files for calibration")
    cal_parser.add_argument("--doses", nargs="+", type=float, required=True, help="Known doses in Gy")
    cal_parser.add_argument("-o", "--output", default="calibration.json", help="Output calibration file")
    cal_parser.add_argument("--dpi", type=float, default=72.0, help="Scanner DPI")

    # --- solve ---
    solve_parser = subparsers.add_parser("solve", help="Convert scanned film to dose")
    solve_parser.add_argument("--film", required=True, help="Treatment film TIFF file")
    solve_parser.add_argument("--cal", required=True, help="Calibration JSON file")
    solve_parser.add_argument("--method", default="micke", choices=_CLI_METHODS,
                              help="Dose solving method")
    solve_parser.add_argument("-o", "--output", default="dose.npy", help="Output dose file (.npy)")
    solve_parser.add_argument("--plot", action="store_true", help="Show dose map plot")

    # --- gamma ---
    gamma_parser = subparsers.add_parser("gamma", help="Gamma analysis between two dose distributions")
    gamma_parser.add_argument("--measured", required=True, help="Measured dose (.npy)")
    gamma_parser.add_argument("--reference", required=True, help="Reference dose (.npy)")
    gamma_parser.add_argument("--criteria", default="3/3", help="Dose%%/DTA(mm), e.g. '3/3'")
    gamma_parser.add_argument("--threshold", type=float, default=10.0, help="Dose threshold (%%)")
    gamma_parser.add_argument("--pixel-size", type=float, default=1.0, help="Pixel size in mm")
    gamma_parser.add_argument("-o", "--output", help="Save gamma map (.npy)")

    # --- report ---
    report_parser = subparsers.add_parser("report", help="Generate PDF QA report")
    report_parser.add_argument("--measured", required=True, help="Measured dose (.npy)")
    report_parser.add_argument("--reference", help="Reference dose (.npy)")
    report_parser.add_argument("--cal", help="Calibration JSON for per-channel info")
    report_parser.add_argument("--method", default="micke", help="Method name for the report")
    report_parser.add_argument("--title", default="Film Dosimetry QA Report", help="Report title")
    report_parser.add_argument("--patient", default="", help="Patient ID")
    report_parser.add_argument("--plan", default="", help="Plan name")
    report_parser.add_argument("-o", "--output", default="report.pdf", help="Output PDF file")

    # --- batch-qa ---
    batch_parser = subparsers.add_parser(
        "batch-qa",
        help="Solve many films and (optionally) gamma-compare each against a reference",
    )
    batch_parser.add_argument("films", nargs="+", help="Treatment film TIFF files")
    batch_parser.add_argument("--cal", required=True, help="Calibration JSON file")
    batch_parser.add_argument("--method", default="micke", choices=_CLI_METHODS,
                              help="Dose solving method")
    batch_parser.add_argument("--ref", help="Shared reference dose (.npy or DICOM RT Dose)")
    batch_parser.add_argument("--criteria", default="3/3", help="Dose%%/DTA(mm) for gamma, e.g. '3/3'")
    batch_parser.add_argument("--threshold", type=float, default=10.0, help="Gamma dose threshold (%%)")
    batch_parser.add_argument("--pixel-size", type=float, default=1.0,
                              help="Film pixel size in mm (used for gamma and DICOM resampling)")
    batch_parser.add_argument("--outdir", default="batch_qa_out", help="Output directory")

    # --- export-dicom ---
    export_parser = subparsers.add_parser(
        "export-dicom", help="Export a dose map (.npy) to a DICOM RT Dose file"
    )
    export_parser.add_argument("--dose", required=True, help="Dose map (.npy), in Gy")
    export_parser.add_argument("--pixel-size", type=float, default=1.0, help="Pixel size in mm")
    export_parser.add_argument("--patient", default="", help="Patient name")
    export_parser.add_argument("--patient-id", default="", help="Patient ID")
    export_parser.add_argument("--plan", default="", help="RT Plan label")
    export_parser.add_argument("--rtplan", help="DICOM RT Plan to read IEC 61217 beam geometry from")
    export_parser.add_argument("-o", "--output", default="dose.dcm", help="Output DICOM file")

    # --- export-sr ---
    sr_parser = subparsers.add_parser(
        "export-sr", help="Export a QA result to a DICOM Structured Report"
    )
    sr_parser.add_argument("--measured", required=True, help="Measured dose (.npy)")
    sr_parser.add_argument("--reference", help="Reference dose (.npy); enables gamma section")
    sr_parser.add_argument("--criteria", default="3/3", help="Dose%%/DTA(mm), e.g. '3/3'")
    sr_parser.add_argument("--threshold", type=float, default=10.0, help="Dose threshold (%%)")
    sr_parser.add_argument("--pixel-size", type=float, default=1.0, help="Pixel size in mm")
    sr_parser.add_argument("--method", default="", help="Dosimetry method name")
    sr_parser.add_argument("--film-type", default="", help="Film model, e.g. EBT3")
    sr_parser.add_argument("--patient", default="", help="Patient name")
    sr_parser.add_argument("--patient-id", default="", help="Patient ID")
    sr_parser.add_argument("--plan", default="", help="RT Plan label")
    sr_parser.add_argument("--study-uid", default="", help="Study Instance UID to group with an existing study")
    sr_parser.add_argument("--series-uid", default="", help="Series Instance UID for the SR series")
    sr_parser.add_argument("--rtplan", help="DICOM RT Plan to read IEC 61217 beam geometry from")
    sr_parser.add_argument("-o", "--output", default="qa_sr.dcm", help="Output DICOM SR file")
    # --- plan-geometry ---
    geom_parser = subparsers.add_parser(
        "plan-geometry", help="List IEC 61217 beam geometry from a DICOM RT Plan"
    )
    geom_parser.add_argument("--plan", required=True, help="DICOM RT Plan file")
    geom_parser.add_argument("--include-setup", action="store_true",
                             help="Include setup beams (excluded by default)")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "calibrate":
        return _cmd_calibrate(args)
    elif args.command == "solve":
        return _cmd_solve(args)
    elif args.command == "gamma":
        return _cmd_gamma(args)
    elif args.command == "report":
        return _cmd_report(args)
    elif args.command == "batch-qa":
        return _cmd_batch_qa(args)
    elif args.command == "export-dicom":
        return _cmd_export_dicom(args)
    elif args.command == "export-sr":
        return _cmd_export_sr(args)
    elif args.command == "plan-geometry":
        return _cmd_plan_geometry(args)

    return 0


def _cmd_calibrate(args: argparse.Namespace) -> int:
    """Run the calibrate command."""
    from chromadose.calibration import Calibration
    from chromadose.core.image import load_tiff

    films = [load_tiff(f) for f in args.films]
    doses = np.array(args.doses)

    if len(films) != len(doses):
        print(f"Error: {len(films)} films but {len(doses)} doses", file=sys.stderr)
        return 1

    # Extract mean pixel values from center of each film
    pixel_values = np.zeros((len(doses), 3))
    for i, film in enumerate(films):
        h, w = film.shape
        # Use central 50% as ROI
        y0, x0 = h // 4, w // 4
        y1, x1 = 3 * h // 4, 3 * w // 4
        pixel_values[i, 0] = np.mean(film.red[y0:y1, x0:x1])
        pixel_values[i, 1] = np.mean(film.green[y0:y1, x0:x1])
        pixel_values[i, 2] = np.mean(film.blue[y0:y1, x0:x1])

    cal = Calibration.from_arrays(
        doses=doses,
        red_pixels=pixel_values[:, 0],
        green_pixels=pixel_values[:, 1],
        blue_pixels=pixel_values[:, 2],
    )
    cal.save(args.output)
    print(f"Calibration saved to {args.output}")
    print(cal.summary())
    return 0


def _cmd_solve(args: argparse.Namespace) -> int:
    """Run the solve command."""
    from chromadose.calibration import Calibration
    from chromadose.core.image import load_tiff
    from chromadose.methods import get_solver

    cal = Calibration.load(args.cal)
    film = load_tiff(args.film)

    solver_cls = get_solver(args.method)
    solver = solver_cls()
    result = solver.solve(film, cal.result)

    np.save(args.output, result.dose)
    print(f"Dose map saved to {args.output}")
    print(f"  Method: {result.method}")
    print(f"  Shape: {result.shape}")
    print(f"  Max dose: {np.max(result.dose):.3f} Gy")
    print(f"  Mean dose: {np.mean(result.dose):.3f} Gy")

    if args.plot:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8, 6))
        plt.imshow(result.dose, cmap="jet")
        plt.colorbar(label="Dose (Gy)")
        plt.title(f"Dose Map — {result.method}")
        plt.show()

    return 0


def _cmd_gamma(args: argparse.Namespace) -> int:
    """Run the gamma command."""
    from chromadose.analysis.gamma import gamma_2d

    measured = np.load(args.measured)
    reference = np.load(args.reference)

    # Parse criteria string "3/3" -> dose=3%, dta=3mm
    parts = args.criteria.split("/")
    dose_crit = float(parts[0])
    dta_crit = float(parts[1])

    result = gamma_2d(
        reference, measured,
        dose_criteria=dose_crit,
        distance_criteria_mm=dta_crit,
        pixel_size_mm=args.pixel_size,
        dose_threshold_pct=args.threshold,
    )

    print(f"Gamma Analysis: {result.criteria}")
    print(f"  Pass rate: {result.pass_rate * 100:.1f}%")
    print(f"  Points evaluated: {result.points_evaluated}")
    print(f"  Points passed: {result.points_passed}")

    if args.output:
        np.save(args.output, result.gamma_map)
        print(f"  Gamma map saved to {args.output}")

    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    """Run the report command."""
    from chromadose.core.types import DoseMap
    from chromadose.io.report import generate_report

    measured = np.load(args.measured)
    reference = np.load(args.reference) if args.reference else None

    # Build a minimal DoseMap
    dm = DoseMap(
        dose=measured,
        uncertainty=np.zeros_like(measured),
        dose_r=measured,
        dose_g=measured,
        dose_b=measured,
        method=args.method,
    )

    # Run gamma if reference is available
    gamma_result = None
    if reference is not None:
        from chromadose.analysis.gamma import gamma_2d
        gamma_result = gamma_2d(reference, measured)

    generate_report(
        args.output, dm,
        gamma_result=gamma_result,
        reference_dose=reference,
        title=args.title,
        patient_id=args.patient,
        plan_name=args.plan,
    )
    print(f"Report saved to {args.output}")
    return 0


def _load_reference_source(path: str) -> NDArray[np.floating] | RTDose:
    """Load the shared reference dose once for the whole batch.

    A NumPy ``.npy`` file is returned as an array (assumed to already be on the
    film grid); a DICOM RT Dose file is returned as an ``RTDose`` object, which
    is resampled to each film's grid later by :func:`_reference_for_film`.
    """
    p = Path(path)
    if p.suffix.lower() == ".npy":
        return np.load(p)

    from chromadose.io.dicom import load_dicom_dose

    return load_dicom_dose(p)


def _reference_for_film(
    ref_source: NDArray[np.floating] | RTDose,
    film_shape: tuple[int, int],
    pixel_size_mm: float,
) -> NDArray[np.floating]:
    """Return the reference dose on a given film's grid.

    Array references are shared as-is; DICOM references are resampled to the
    film grid using their maximum-dose slice.
    """
    if isinstance(ref_source, np.ndarray):
        return ref_source

    from chromadose.io.dicom import resample_to_film

    slice_index, _ = ref_source.max_dose_slice()
    return resample_to_film(ref_source, film_shape, pixel_size_mm, slice_index)


def _cmd_batch_qa(args: argparse.Namespace) -> int:
    """Run the batch-qa command over many films with a shared calibration."""
    from chromadose.analysis.gamma import gamma_2d
    from chromadose.calibration import Calibration
    from chromadose.core.image import load_tiff
    from chromadose.methods import get_solver

    dose_crit, dta_crit = (float(x) for x in args.criteria.split("/"))

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cal = Calibration.load(args.cal)
    solver = get_solver(args.method)()

    # Load the shared reference once — parsing a DICOM RT Dose (or even a .npy)
    # on every film would dominate the runtime of a large batch. A failure here
    # is fatal since the requested gamma analysis can't run for any film.
    ref_source: NDArray[np.floating] | RTDose | None = None
    if args.ref:
        try:
            ref_source = _load_reference_source(args.ref)
        except Exception as exc:  # noqa: BLE001
            print(f"Error loading reference '{args.ref}': {exc}", file=sys.stderr)
            return 1

    summary_lines = ["film,max_dose_Gy,mean_dose_Gy,gamma_pass_rate_pct"]
    failures = 0

    for film_path in args.films:
        name = Path(film_path).stem
        # Wrap the whole per-film pipeline so a failure in any step (load,
        # solve, resample, gamma, save) is reported and the batch continues.
        try:
            film = load_tiff(film_path)
            result = solver.solve(film, cal.result)

            np.save(outdir / f"{name}_dose.npy", result.dose)

            pass_rate_str = ""
            pass_rate_pct = ""
            if ref_source is not None:
                reference = _reference_for_film(ref_source, result.dose.shape, args.pixel_size)
                gamma = gamma_2d(
                    reference, result.dose,
                    dose_criteria=dose_crit,
                    distance_criteria_mm=dta_crit,
                    pixel_size_mm=args.pixel_size,
                    dose_threshold_pct=args.threshold,
                )
                np.save(outdir / f"{name}_gamma.npy", gamma.gamma_map)
                pass_rate_pct = f"{gamma.pass_rate * 100:.1f}"
                pass_rate_str = f"  gamma {gamma.criteria}: {pass_rate_pct}% pass"

            print(
                f"[ OK ] {name}: max {np.max(result.dose):.3f} Gy, "
                f"mean {np.mean(result.dose):.3f} Gy{pass_rate_str}"
            )
            summary_lines.append(
                f"{name},{np.max(result.dose):.4f},{np.mean(result.dose):.4f},{pass_rate_pct}"
            )
        except Exception as exc:  # noqa: BLE001 — report and continue the batch
            print(f"[FAIL] {film_path}: {exc}", file=sys.stderr)
            summary_lines.append(f"{name},,,")
            failures += 1
            continue

    summary_path = outdir / "summary.csv"
    summary_path.write_text("\n".join(summary_lines) + "\n")

    n_ok = len(args.films) - failures
    print(f"\nProcessed {n_ok}/{len(args.films)} films -> {outdir}/ (summary.csv)")
    return 1 if failures else 0


def _geometry_from_rtplan(path: str | None) -> BeamGeometry | None:
    """Load the first treatment beam's IEC 61217 geometry from an RT Plan."""
    if not path:
        return None

    from chromadose.io.dicom import load_beam_geometry

    try:
        beams = load_beam_geometry(path)
    except Exception as exc:  # noqa: BLE001 — surface a clean CLI error, not a traceback
        print(f"Error loading RT Plan '{path}': {exc}", file=sys.stderr)
        sys.exit(1)

    if not beams:
        print(f"Warning: no treatment beams in {path}; geometry not recorded", file=sys.stderr)
        return None
    if len(beams) > 1:
        label = beams[0].beam_name or "beam 1"
        print(
            f"Note: RT Plan has {len(beams)} beams; recording geometry of the first ({label})",
            file=sys.stderr,
        )
    return beams[0]


def _cmd_export_dicom(args: argparse.Namespace) -> int:
    """Run the export-dicom command."""
    from chromadose.io.dicom import save_dicom_dose

    dose = np.load(args.dose)
    save_dicom_dose(
        dose,
        args.output,
        pixel_spacing_mm=(args.pixel_size, args.pixel_size),
        patient_name=args.patient,
        patient_id=args.patient_id,
        plan_label=args.plan,
        geometry=_geometry_from_rtplan(args.rtplan),
    )
    print(f"RT Dose saved to {args.output}")
    print(f"  Shape: {dose.shape}")
    print(f"  Max dose: {np.max(dose):.3f} Gy")
    return 0


def _cmd_export_sr(args: argparse.Namespace) -> int:
    """Run the export-sr command."""
    from chromadose.io.dicom_sr import save_dicom_sr

    measured = np.load(args.measured)

    gamma_result = None
    if args.reference:
        from chromadose.analysis.gamma import gamma_2d

        reference = np.load(args.reference)
        dose_crit, dta_crit = (float(x) for x in args.criteria.split("/"))
        gamma_result = gamma_2d(
            reference, measured,
            dose_criteria=dose_crit,
            distance_criteria_mm=dta_crit,
            pixel_size_mm=args.pixel_size,
            dose_threshold_pct=args.threshold,
        )

    save_dicom_sr(
        args.output,
        gamma_result=gamma_result,
        max_dose_gy=float(np.max(measured)),
        mean_dose_gy=float(np.mean(measured)),
        method=args.method,
        film_type=args.film_type,
        patient_name=args.patient,
        patient_id=args.patient_id,
        plan_label=args.plan,
        study_instance_uid=args.study_uid,
        series_instance_uid=args.series_uid,
        geometry=_geometry_from_rtplan(args.rtplan),
    )
    print(f"DICOM SR saved to {args.output}")
    if gamma_result is not None:
        print(f"  Gamma {gamma_result.criteria}: {gamma_result.pass_rate * 100:.1f}% pass")
    return 0


def _cmd_plan_geometry(args: argparse.Namespace) -> int:
    """Run the plan-geometry command."""
    from chromadose.io.dicom import load_beam_geometry

    beams = load_beam_geometry(args.plan, include_setup=args.include_setup)
    if not beams:
        print("No beams found in plan.")
        return 0

    print(f"{len(beams)} beam(s) — IEC 61217 angles in degrees:")
    print(f"  {'#':>3}  {'name':<14} {'gantry':>7} {'coll':>7} {'couch':>7}  energy")
    for b in beams:
        number = b.beam_number if b.beam_number is not None else "-"
        energy = f"{b.beam_energy_mv:g} MV" if b.beam_energy_mv is not None else "-"
        print(
            f"  {number:>3}  {b.beam_name:<14} "
            f"{b.gantry_angle:>7.1f} {b.collimator_angle:>7.1f} {b.couch_angle:>7.1f}  {energy}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
