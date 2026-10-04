"""Numerically find and label intersections between plotted functions."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

import numpy as np

from graphing.plotter import PlotSeries


@dataclass(frozen=True)
class IntersectionPoint:
    identifier: str
    x: float
    y: float
    expressions: tuple[str, ...]


def _evaluate_difference(first: PlotSeries, second: PlotSeries, x: float) -> tuple[float, float, float]:
    try:
        with np.errstate(all="ignore"):
            first_y = float(np.asarray(first.function(x)))
            second_y = float(np.asarray(second.function(x)))
        difference = first_y - second_y
    except (ArithmeticError, TypeError, ValueError, OverflowError):
        return float("nan"), float("nan"), float("nan")
    if not np.isfinite(first_y) or not np.isfinite(second_y) or not np.isfinite(difference):
        return float("nan"), float("nan"), float("nan")
    return first_y, second_y, difference


def _bisect_intersection(
    first: PlotSeries,
    second: PlotSeries,
    left: float,
    right: float,
    left_difference: float,
    tolerance: float,
) -> tuple[float, float] | None:
    for _ in range(64):
        middle = (left + right) / 2
        first_y, second_y, difference = _evaluate_difference(first, second, middle)
        if not np.isfinite(difference):
            return None
        if abs(difference) <= tolerance * max(1.0, abs(first_y), abs(second_y)):
            return middle, (first_y + second_y) / 2
        if (left_difference < 0) == (difference < 0):
            left = middle
            left_difference = difference
        else:
            right = middle
    middle = (left + right) / 2
    first_y, second_y, difference = _evaluate_difference(first, second, middle)
    if abs(difference) > tolerance * max(1.0, abs(first_y), abs(second_y)):
        return None
    return middle, (first_y + second_y) / 2


def _minimize_absolute_difference(
    first: PlotSeries,
    second: PlotSeries,
    left: float,
    right: float,
) -> tuple[float, float] | None:
    ratio = (np.sqrt(5.0) - 1.0) / 2.0
    first_x = right - ratio * (right - left)
    second_x = left + ratio * (right - left)
    first_value = abs(_evaluate_difference(first, second, first_x)[2])
    second_value = abs(_evaluate_difference(first, second, second_x)[2])

    for _ in range(48):
        if first_value <= second_value:
            right = second_x
            second_x = first_x
            second_value = first_value
            first_x = right - ratio * (right - left)
            first_value = abs(_evaluate_difference(first, second, first_x)[2])
        else:
            left = first_x
            first_x = second_x
            first_value = second_value
            second_x = left + ratio * (right - left)
            second_value = abs(_evaluate_difference(first, second, second_x)[2])

    x = (left + right) / 2
    first_y, second_y, difference = _evaluate_difference(first, second, x)
    if not np.isfinite(difference) or abs(difference) > 1e-7 * max(1.0, abs(first_y), abs(second_y)):
        return None
    return x, (first_y + second_y) / 2


def _make_identifier(index: int) -> str:
    identifier = ""
    while index >= 0:
        index, remainder = divmod(index, 26)
        identifier = chr(ord("A") + remainder) + identifier
        index -= 1
    return identifier


def find_intersections(
    series: Sequence[PlotSeries],
    x_min: float,
    x_max: float,
    samples: int = 4097,
) -> list[IntersectionPoint]:
    """Return unique pairwise intersections in the requested x interval."""
    if len(series) < 2 or not np.isfinite(x_min) or not np.isfinite(x_max) or x_min >= x_max:
        return []

    x_values = np.linspace(x_min, x_max, max(samples, 3))
    x_tolerance = max(abs(x_max - x_min) * 1e-8, 1e-10)
    tolerance = 1e-9
    points: list[dict[str, object]] = []

    for first, second in combinations(series, 2):
        try:
            with np.errstate(all="ignore"):
                first_values = np.asarray(first.function(x_values), dtype=float)
                second_values = np.asarray(second.function(x_values), dtype=float)
            first_values = np.broadcast_to(first_values, x_values.shape)
            second_values = np.broadcast_to(second_values, x_values.shape)
            differences = first_values - second_values
        except (ArithmeticError, TypeError, ValueError, OverflowError):
            continue

        valid = np.isfinite(first_values) & np.isfinite(second_values) & np.isfinite(differences)
        if np.count_nonzero(valid) < 3 or np.nanmax(np.abs(differences[valid])) <= tolerance:
            continue

        pair_points: list[tuple[float, float]] = []
        for index in range(len(x_values) - 1):
            if not valid[index] or not valid[index + 1]:
                continue
            left_difference = float(differences[index])
            right_difference = float(differences[index + 1])
            if left_difference == 0:
                pair_points.append((float(x_values[index]), float((first_values[index] + second_values[index]) / 2)))
            elif (left_difference < 0) != (right_difference < 0):
                refined = _bisect_intersection(
                    first,
                    second,
                    float(x_values[index]),
                    float(x_values[index + 1]),
                    left_difference,
                    tolerance,
                )
                if refined is not None:
                    pair_points.append(refined)

        if valid[-1] and differences[-1] == 0:
            pair_points.append((float(x_values[-1]), float((first_values[-1] + second_values[-1]) / 2)))

        absolute_differences = np.where(valid, np.abs(differences), np.inf)
        for index in range(1, len(x_values) - 1):
            if (
                absolute_differences[index] <= absolute_differences[index - 1]
                and absolute_differences[index] <= absolute_differences[index + 1]
                and absolute_differences[index] != 0
            ):
                refined = _minimize_absolute_difference(
                    first,
                    second,
                    float(x_values[index - 1]),
                    float(x_values[index + 1]),
                )
                if refined is not None:
                    pair_points.append(refined)

        for x, y in pair_points:
            match = next(
                (
                    point
                    for point in points
                    if abs(x - float(point["x"])) <= x_tolerance
                    and abs(y - float(point["y"])) <= max(1e-8, abs(y) * 1e-8)
                ),
                None,
            )
            if match is not None:
                expressions = match["expressions"]
                assert isinstance(expressions, set)
                expressions.update((first.label, second.label))
            else:
                points.append({"x": x, "y": y, "expressions": {first.label, second.label}})

    points.sort(key=lambda point: (float(point["x"]), float(point["y"])))
    return [
        IntersectionPoint(
            identifier=_make_identifier(index),
            x=float(point["x"]),
            y=float(point["y"]),
            expressions=tuple(sorted(point["expressions"])),
        )
        for index, point in enumerate(points)
    ]