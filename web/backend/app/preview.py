"""Render dose / gamma arrays to base64 PNG previews for the web UI.

Uses the non-interactive Agg backend so it runs headless on a server.
"""

from __future__ import annotations

import base64
import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  (must follow matplotlib.use)
import numpy as np  # noqa: E402
from numpy.typing import NDArray  # noqa: E402


def array_to_png_datauri(
    array: NDArray[np.floating],
    *,
    label: str,
    cmap: str = "turbo",
    vmin: float | None = None,
    vmax: float | None = None,
) -> str:
    """Render a 2D array to a colour-mapped PNG and return it as a data URI."""
    fig, ax = plt.subplots(figsize=(5.0, 4.0), dpi=100)
    try:
        image = ax.imshow(array, cmap=cmap, vmin=vmin, vmax=vmax)
        fig.colorbar(image, ax=ax, label=label)
        ax.set_xticks([])
        ax.set_yticks([])
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight")
    finally:
        plt.close(fig)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
