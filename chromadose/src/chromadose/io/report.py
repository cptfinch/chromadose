"""PDF report generation for film dosimetry QA.

Generates a single-page or multi-page PDF report containing:
- Dose map visualization
- Gamma analysis results
- Dose profiles with TPS comparison
- Summary statistics

Uses matplotlib for rendering — no external PDF libraries needed.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for report generation

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from numpy.typing import NDArray

if TYPE_CHECKING:
    from chromadose.analysis.gamma import GammaResult
    from chromadose.analysis.profiles import ProfileComparison
    from chromadose.core.types import DoseMap


def generate_report(
    output_path: str | Path,
    dose_map: DoseMap,
    gamma_result: GammaResult | None = None,
    profiles: list[ProfileComparison] | None = None,
    reference_dose: NDArray[np.floating] | None = None,
    title: str = "Film Dosimetry QA Report",
    patient_id: str = "",
    plan_name: str = "",
    analyst: str = "",
    notes: str = "",
) -> Path:
    """Generate a PDF QA report.

    Parameters:
        output_path: Where to save the PDF.
        dose_map: The measured dose map.
        gamma_result: Optional gamma analysis result.
        profiles: Optional list of profile comparisons.
        reference_dose: Optional reference (TPS) dose for comparison.
        title: Report title.
        patient_id: Patient identifier.
        plan_name: Treatment plan name.
        analyst: Name of the analyst.
        notes: Additional notes.

    Returns:
        Path to the generated PDF.
    """
    output_path = Path(output_path)

    with PdfPages(str(output_path)) as pdf:
        # Page 1: Dose map + summary
        _page_dose_map(pdf, dose_map, reference_dose, title, patient_id, plan_name, analyst, notes)

        # Page 2: Gamma analysis (if provided)
        if gamma_result is not None:
            _page_gamma(pdf, gamma_result, dose_map)

        # Page 3: Profiles (if provided)
        if profiles:
            _page_profiles(pdf, profiles)

    return output_path


def _page_dose_map(
    pdf: PdfPages,
    dose_map: DoseMap,
    reference_dose: NDArray[np.floating] | None,
    title: str,
    patient_id: str,
    plan_name: str,
    analyst: str,
    notes: str,
) -> None:
    """First page: dose maps and header."""
    has_ref = reference_dose is not None
    ncols = 2 if has_ref else 1

    fig, axes = plt.subplots(1, ncols, figsize=(11, 8.5))
    if ncols == 1:
        axes = [axes]

    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98)

    # Header text
    header_lines = []
    if patient_id:
        header_lines.append(f"Patient: {patient_id}")
    if plan_name:
        header_lines.append(f"Plan: {plan_name}")
    header_lines.append(f"Method: {dose_map.method}")
    header_lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if analyst:
        header_lines.append(f"Analyst: {analyst}")

    header_text = "  |  ".join(header_lines)
    fig.text(0.5, 0.94, header_text, ha="center", fontsize=8, color="gray")

    # Measured dose map
    vmax = float(np.nanmax(dose_map.dose))
    im = axes[0].imshow(dose_map.dose, cmap="jet", vmin=0, vmax=vmax)
    axes[0].set_title("Measured Dose (Gy)")
    plt.colorbar(im, ax=axes[0], fraction=0.046, pad=0.04)

    # Reference dose map (if available)
    if has_ref and reference_dose is not None:
        im2 = axes[1].imshow(reference_dose, cmap="jet", vmin=0, vmax=vmax)
        axes[1].set_title("Reference Dose (Gy)")
        plt.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04)

    # Statistics box
    stats_text = (
        f"Max dose: {float(np.nanmax(dose_map.dose)):.3f} Gy\n"
        f"Mean dose: {float(np.nanmean(dose_map.dose)):.3f} Gy\n"
        f"Image size: {dose_map.shape[0]}x{dose_map.shape[1]} px"
    )
    if notes:
        stats_text += f"\n\nNotes: {notes}"

    fig.text(
        0.5, 0.02, stats_text, ha="center", fontsize=8,
        bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
    )

    plt.tight_layout(rect=[0, 0.08, 1, 0.92])
    pdf.savefig(fig)
    plt.close(fig)


def _page_gamma(
    pdf: PdfPages,
    gamma_result: GammaResult,
    dose_map: DoseMap,
) -> None:
    """Second page: gamma analysis results."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5))

    fig.suptitle(f"Gamma Analysis — {gamma_result.criteria}", fontsize=14, fontweight="bold")

    # Gamma map
    gmap = gamma_result.gamma_map
    im = axes[0].imshow(gmap, cmap="RdYlGn_r", vmin=0, vmax=2.0)
    axes[0].set_title("Gamma Index Map")
    plt.colorbar(im, ax=axes[0], fraction=0.046, pad=0.04)

    # Pass/fail overlay
    pass_fail = np.where(np.isnan(gmap), 0.5, np.where(gmap <= 1.0, 1.0, 0.0))
    axes[1].imshow(pass_fail, cmap="RdYlGn", vmin=0, vmax=1)
    axes[1].set_title("Pass (green) / Fail (red)")

    # Statistics
    pass_pct = gamma_result.pass_rate * 100
    color = "green" if pass_pct >= 95 else ("orange" if pass_pct >= 90 else "red")

    stats_text = (
        f"Pass rate: {pass_pct:.1f}%\n"
        f"Points evaluated: {gamma_result.points_evaluated}\n"
        f"Points passed: {gamma_result.points_passed}\n"
        f"Dose threshold: {gamma_result.dose_threshold_pct:.0f}%"
    )

    fig.text(
        0.5, 0.02, stats_text, ha="center", fontsize=10, fontweight="bold",
        color=color,
        bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
    )

    plt.tight_layout(rect=[0, 0.08, 1, 0.93])
    pdf.savefig(fig)
    plt.close(fig)


def _page_profiles(
    pdf: PdfPages,
    profiles: list[ProfileComparison],
) -> None:
    """Third page: dose profiles."""
    n = len(profiles)
    fig, axes = plt.subplots(n, 1, figsize=(11, 8.5), squeeze=False)

    fig.suptitle("Dose Profiles", fontsize=14, fontweight="bold")

    for i, comp in enumerate(profiles):
        ax = axes[i, 0]
        ax.plot(
            comp.reference.position_mm, comp.reference.dose,
            "b-", linewidth=1.5, label=f"Reference ({comp.reference.label})",
        )
        ax.plot(
            comp.evaluated.position_mm, comp.evaluated.dose,
            "r--", linewidth=1.5, label=f"Film ({comp.evaluated.label})",
        )
        ax.set_xlabel("Position (mm)")
        ax.set_ylabel("Dose (Gy)")
        ax.legend(fontsize=8)
        ax.set_title(
            f"{comp.reference.label} — "
            f"Mean diff: {comp.mean_abs_diff_pct:.1f}%, "
            f"Max diff: {comp.max_abs_diff_pct:.1f}%",
            fontsize=9,
        )
        ax.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    pdf.savefig(fig)
    plt.close(fig)
