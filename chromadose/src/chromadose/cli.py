"""Command-line interface for chromadose.

Usage:
    chromadose calibrate --films cal1.tif cal2.tif --doses 0 0.5 1 2 4 7 -o cal.json
    chromadose solve --film treatment.tif --cal cal.json --method micke -o dose.npy
    chromadose gamma --measured dose.npy --reference tps_dose.npy --criteria 3/3
    chromadose report --measured dose.npy --gamma gamma.npz -o report.pdf

Uses argparse (stdlib) to avoid extra dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="chromadose",
        description="Modern multichannel radiochromic film dosimetry",
    )
    parser.add_argument("--version", action="version", version="chromadose 1.0.0")

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
    solve_parser.add_argument("--method", default="micke", choices=["micke", "mayer", "multigaussian"],
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

    return 0


def _cmd_calibrate(args: argparse.Namespace) -> int:
    """Run the calibrate command."""
    from chromadose.calibration import Calibration
    from chromadose.core.image import load_tiff
    from chromadose.core.utils import roi_mean

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


if __name__ == "__main__":
    sys.exit(main())
