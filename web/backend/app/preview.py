"""Render dose / gamma arrays to base64 PNG previews for the web UI.

Uses matplotlib's object-oriented ``Figure`` API with an explicit Agg canvas
rather than the stateful ``pyplot`` interface: the web server serves requests
from a thread pool, and ``pyplot``'s global figure registry is not thread-safe.
Constructing a standalone ``Figure`` keeps each render fully isolated.
"""

from __future__ import annotations

import base64
import io

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import numpy as np
from numpy.typing import NDArray


def array_to_png_datauri(
    array: NDArray[np.floating],
    *,
    label: str,
    cmap: str = "turbo",
    vmin: float | None = None,
    vmax: float | None = None,
) -> str:
    """Render a 2D array to a colour-mapped PNG and return it as a data URI."""
    fig = Figure(figsize=(5.0, 4.0), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    image = ax.imshow(array, cmap=cmap, vmin=vmin, vmax=vmax)
    fig.colorbar(image, ax=ax, label=label)
    ax.set_xticks([])
    ax.set_yticks([])
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
