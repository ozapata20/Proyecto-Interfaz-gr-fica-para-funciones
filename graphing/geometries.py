"""Render selectable two- and three-dimensional geometric figures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from matplotlib.axes import Axes
from matplotlib.patches import Circle, Rectangle


@dataclass(frozen=True)
class GeometricFigure:
    identifier: str
    kind: str
    parameters: dict[str, float]
    color: str


def render_geometry_2d(
    axes: Axes,
    figures: Sequence[GeometricFigure],
    x_limits: tuple[float, float],
    y_limits: tuple[float, float] | None,
    *,
    dark_mode: bool = False,
    preserve_view: bool = False,
) -> None:
    view_limits = (axes.get_xlim(), axes.get_ylim()) if preserve_view else None
    background = "#29322d" if dark_mode else "#ffffff"
    foreground = "#e6ece7" if dark_mode else "#18231d"
    muted = "#a3b0a7" if dark_mode else "#657168"
    grid = "#3d4942" if dark_mode else "#e5e9e3"
    spine = "#536158" if dark_mode else "#d8ded7"
    axes.clear()
    axes.set_facecolor(background)
    axes.set_xlim(*(view_limits[0] if view_limits else x_limits))
    axes.set_ylim(*(view_limits[1] if view_limits else y_limits or x_limits))
    axes.set_aspect("equal", adjustable="box")
    axes.grid(True, color=grid, linewidth=0.8)
    axes.axhline(0, color=muted, linewidth=1.5, zorder=1)
    axes.axvline(0, color=muted, linewidth=1.5, zorder=1)
    axes.set_xlabel("x", color=foreground)
    axes.set_ylabel("y", color=foreground)
    axes.tick_params(colors=muted, labelsize=9)
    for axis_spine in axes.spines.values():
        axis_spine.set_color(spine)

    for figure in figures:
        parameters = figure.parameters
        if figure.kind == "Punto":
            axes.scatter(
                [parameters["x"]],
                [parameters["y"]],
                color=figure.color,
                s=55,
                label=figure.identifier,
                zorder=3,
            )
        elif figure.kind == "Círculo":
            axes.add_patch(
                Circle(
                    (parameters["x"], parameters["y"]),
                    parameters["r"],
                    fill=False,
                    edgecolor=figure.color,
                    linewidth=2,
                    label=figure.identifier,
                )
            )
        elif figure.kind == "Rectángulo":
            axes.add_patch(
                Rectangle(
                    (parameters["x"], parameters["y"]),
                    parameters["width"],
                    parameters["height"],
                    fill=False,
                    edgecolor=figure.color,
                    linewidth=2,
                    label=figure.identifier,
                )
            )

    if figures:
        axes.legend(loc="upper left", framealpha=0.9, fontsize=9)
        legend = axes.get_legend()
        if legend is not None:
            legend.get_frame().set_facecolor(background)
            legend.get_frame().set_edgecolor(spine)
            for text in legend.get_texts():
                text.set_color(foreground)
    else:
        axes.text(
            0.5,
            0.5,
            "Añade una figura geométrica para empezar",
            transform=axes.transAxes,
            ha="center",
            va="center",
            color=muted,
            fontsize=12,
        )
    axes.figure.tight_layout(pad=2.0)


def render_geometry_3d(
    axes: Axes,
    figures: Sequence[GeometricFigure],
    x_limits: tuple[float, float],
    y_limits: tuple[float, float] | None,
    *,
    dark_mode: bool = False,
    preserve_view: bool = False,
) -> None:
    view_limits = (
        (axes.get_xlim(), axes.get_ylim(), axes.get_zlim()) if preserve_view else None
    )
    background = "#29322d" if dark_mode else "#ffffff"
    foreground = "#e6ece7" if dark_mode else "#18231d"
    grid = "#3d4942" if dark_mode else "#e5e9e3"
    axes.clear()
    axes.set_facecolor(background)
    axes.set_xlim(*x_limits)
    axes.set_ylim(*x_limits)
    axes.set_zlim(*(y_limits or x_limits))
    axes.set_xlabel("x", color=foreground)
    axes.set_ylabel("y", color=foreground)
    axes.set_zlabel("z", color=foreground)
    axes.tick_params(colors=foreground, labelsize=8)
    axes.grid(True, color=grid, linewidth=0.8)
    axes.set_box_aspect((1, 1, 1))
    for axis in (axes.xaxis, axes.yaxis, axes.zaxis):
        axis.pane.set_facecolor(background)
        axis.pane.set_edgecolor(grid)

    coordinates = np.linspace(*x_limits, 48)
    x_values, y_values = np.meshgrid(coordinates, coordinates)
    for figure in figures:
        parameters = figure.parameters
        if figure.kind == "Esfera":
            azimuth = np.linspace(0, 2 * np.pi, 48)
            elevation = np.linspace(0, np.pi, 32)
            sphere_x = parameters["x"] + parameters["r"] * np.outer(
                np.cos(azimuth), np.sin(elevation)
            )
            sphere_y = parameters["y"] + parameters["r"] * np.outer(
                np.sin(azimuth), np.sin(elevation)
            )
            sphere_z = parameters["z"] + parameters["r"] * np.outer(
                np.ones_like(azimuth), np.cos(elevation)
            )
            axes.plot_surface(
                sphere_x,
                sphere_y,
                sphere_z,
                color=figure.color,
                alpha=0.72,
                linewidth=0,
                label=figure.identifier,
            )
        elif figure.kind == "Plano":
            plane_z = parameters["a"] * x_values + parameters["b"] * y_values + parameters["c"]
            axes.plot_surface(
                x_values,
                y_values,
                plane_z,
                color=figure.color,
                alpha=0.58,
                linewidth=0,
                label=figure.identifier,
            )

    axes.set_xlim(*(view_limits[0] if view_limits else x_limits))
    axes.set_ylim(*(view_limits[1] if view_limits else x_limits))
    axes.set_zlim(*(view_limits[2] if view_limits else y_limits or x_limits))
    if not figures:
        axes.text2D(
            0.5,
            0.5,
            "Añade una figura geométrica para empezar",
            transform=axes.transAxes,
            ha="center",
            va="center",
            color=foreground,
        )
    axes.figure.tight_layout(pad=2.0)
