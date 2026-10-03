"""Draw parsed functions into a Matplotlib axes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


@dataclass(frozen=True)
class PlotSeries:
    label: str
    function: Callable[[np.ndarray], object]
    color: str


class PlotRenderer:
    """Render selected functions and keep the y-range useful for outliers."""

    def __init__(self, figure: Figure, axes: Axes, draw: Callable[[], None]) -> None:
        self.figure = figure
        self.axes = axes
        self._draw = draw

    def render(self, series: Sequence[PlotSeries], x_min: float, x_max: float) -> None:
        axes = self.axes
        axes.clear()
        axes.set_facecolor("#ffffff")
        axes.set_xlim(x_min, x_max)
        axes.grid(True, color="#e5e9e3", linewidth=0.8)
        axes.axhline(0, color="#8e9991", linewidth=0.9, zorder=1)
        axes.axvline(0, color="#8e9991", linewidth=0.9, zorder=1)
        axes.set_xlabel("x", color="#39443d")
        axes.set_ylabel("y", color="#39443d")
        axes.tick_params(colors="#657168", labelsize=9)
        for spine in axes.spines.values():
            spine.set_color("#d8ded7")

        if not series:
            axes.text(
                0.5,
                0.5,
                "Añade una función para empezar",
                transform=axes.transAxes,
                ha="center",
                va="center",
                color="#7a857d",
                fontsize=12,
            )
            self.figure.tight_layout(pad=2.0)
            self._draw()
            return

        x_values = np.linspace(x_min, x_max, 1400)
        plotted_values: list[np.ndarray] = []
        for item in series:
            try:
                with np.errstate(all="ignore"):
                    values = np.asarray(item.function(x_values), dtype=float)
                if values.ndim == 0:
                    values = np.full_like(x_values, float(values))
                values = np.broadcast_to(values, x_values.shape).copy()
            except (ArithmeticError, TypeError, ValueError):
                values = np.full_like(x_values, np.nan)

            values[~np.isfinite(values) | (np.abs(values) > 1e8)] = np.nan
            axes.plot(x_values, values, color=item.color, linewidth=2.0, label=item.label)
            finite = values[np.isfinite(values)]
            if finite.size:
                plotted_values.append(finite)

        if plotted_values:
            visible = np.concatenate(plotted_values)
            lower, upper = np.percentile(visible, [2, 98])
            if lower == upper:
                padding = max(abs(float(lower)) * 0.1, 1.0)
            else:
                padding = (upper - lower) * 0.12
            axes.set_ylim(float(lower - padding), float(upper + padding))

        axes.legend(loc="upper left", frameon=True, framealpha=0.92, fontsize=9)
        self.figure.tight_layout(pad=2.0)
        self._draw()