"""Calculate useful characteristics for parsed mathematical functions."""

from __future__ import annotations

import ast
from dataclasses import dataclass

import numpy as np

from utils.reader import ParsedFunction


@dataclass(frozen=True)
class FunctionAnalysis:
    is_polynomial: bool
    degree: int | None
    x_intercepts: tuple[float, ...] | None
    y_intercept: float | None
    vertex: tuple[float, float] | None
    slope: float | None = None
    concavity: str | None = None
    symmetry_axis: float | None = None
    inflection_point: tuple[float, float] | None = None
    is_zero_function: bool = False


def _polynomial_coefficients(node: ast.AST) -> np.ndarray | None:
    if isinstance(node, ast.Expression):
        return _polynomial_coefficients(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        value = float(node.value)
        return np.array([value]) if np.isfinite(value) else None
    if isinstance(node, ast.Name) and node.id == "x":
        return np.array([0.0, 1.0])
    if isinstance(node, ast.UnaryOp):
        coefficients = _polynomial_coefficients(node.operand)
        if coefficients is None:
            return None
        if isinstance(node.op, ast.UAdd):
            return coefficients
        if isinstance(node.op, ast.USub):
            return -coefficients
        return None
    if not isinstance(node, ast.BinOp):
        return None

    left = _polynomial_coefficients(node.left)
    right = _polynomial_coefficients(node.right)
    if left is None or right is None:
        return None
    if isinstance(node.op, ast.Add):
        return np.polynomial.polynomial.polyadd(left, right)
    if isinstance(node.op, ast.Sub):
        return np.polynomial.polynomial.polysub(left, right)
    if isinstance(node.op, ast.Mult):
        return np.polynomial.polynomial.polymul(left, right)
    if isinstance(node.op, ast.Div) and right.size == 1 and right[0] != 0:
        return left / right[0]
    if (
        isinstance(node.op, ast.Pow)
        and right.size == 1
        and right[0].is_integer()
        and 0 <= right[0] <= 64
    ):
        return np.polynomial.polynomial.polypow(left, int(right[0]))
    return None


def _real_roots(coefficients: np.ndarray) -> tuple[float, ...]:
    trimmed = coefficients.copy()
    while trimmed.size > 1 and trimmed[-1] == 0:
        trimmed = trimmed[:-1]
    if trimmed.size == 1:
        return ()

    roots = np.polynomial.polynomial.polyroots(trimmed)
    real_roots = sorted(
        float(root.real)
        for root in roots
        if abs(float(root.imag)) <= 1e-8 * max(1.0, abs(float(root.real)))
    )
    unique_roots: list[float] = []
    for root in real_roots:
        if not unique_roots or not np.isclose(root, unique_roots[-1], rtol=1e-8, atol=1e-10):
            unique_roots.append(root)
    return tuple(unique_roots)


def _numeric_roots(
    function: ParsedFunction,
    x_min: float,
    x_max: float,
) -> tuple[float, ...]:
    x_values = np.linspace(x_min, x_max, 2049)
    with np.errstate(all="ignore"):
        y_values = np.asarray(function(x_values), dtype=float)
    y_values = np.broadcast_to(y_values, x_values.shape)
    valid = np.isfinite(y_values)
    roots: list[float] = []

    for index in range(len(x_values) - 1):
        if not valid[index] or not valid[index + 1]:
            continue
        left_value = float(y_values[index])
        right_value = float(y_values[index + 1])
        if left_value == 0:
            roots.append(float(x_values[index]))
        elif (left_value < 0) != (right_value < 0):
            value_scale = max(1.0, abs(left_value), abs(right_value))
            left = float(x_values[index])
            right = float(x_values[index + 1])
            invalid_midpoint = False
            for _ in range(60):
                middle = (left + right) / 2
                try:
                    middle_value = float(function(middle))
                except (ArithmeticError, TypeError, ValueError, OverflowError):
                    invalid_midpoint = True
                    break
                if not np.isfinite(middle_value):
                    invalid_midpoint = True
                    break
                if middle_value == 0:
                    left = right = middle
                    break
                if (left_value < 0) == (middle_value < 0):
                    left = middle
                    left_value = middle_value
                else:
                    right = middle
            root = (left + right) / 2
            try:
                root_value = float(function(root))
            except (ArithmeticError, TypeError, ValueError, OverflowError):
                invalid_midpoint = True
                root_value = float("inf")
            if not invalid_midpoint and abs(root_value) <= 1e-7 * value_scale:
                roots.append(root)

    if valid[-1] and y_values[-1] == 0:
        roots.append(float(x_values[-1]))
    return tuple(root for index, root in enumerate(roots) if index == 0 or not np.isclose(
        root, roots[index - 1], rtol=1e-8, atol=1e-10
    ))


def _finite_value(function: ParsedFunction, x_value: float) -> float | None:
    try:
        with np.errstate(all="ignore"):
            value = float(np.asarray(function(x_value)))
    except (ArithmeticError, TypeError, ValueError, OverflowError):
        return None
    return value if np.isfinite(value) else None


def analyze_function(
    function: ParsedFunction,
    x_min: float | None = None,
    x_max: float | None = None,
) -> FunctionAnalysis:
    """Return intercepts and characteristic points for low-degree polynomials."""
    coefficients = _polynomial_coefficients(function._tree)
    y_intercept = _finite_value(function, 0.0)

    if coefficients is not None:
        while coefficients.size > 1 and coefficients[-1] == 0:
            coefficients = coefficients[:-1]
        zero_function = coefficients.size == 1 and coefficients[0] == 0
        degree = None if zero_function else coefficients.size - 1
        x_intercepts = _real_roots(coefficients)
        vertex = None
        slope = None
        concavity = None
        symmetry_axis = None
        inflection_point = None
        if degree == 1:
            slope = float(coefficients[1])
        if degree == 2:
            a, b = float(coefficients[2]), float(coefficients[1])
            vertex_x = -b / (2 * a)
            vertex_y = _finite_value(function, vertex_x)
            if vertex_y is not None:
                vertex = (vertex_x, vertex_y)
            concavity = "hacia arriba" if a > 0 else "hacia abajo"
            symmetry_axis = vertex_x
        if degree == 3:
            a, b = float(coefficients[3]), float(coefficients[2])
            inflection_x = -b / (3 * a)
            inflection_y = _finite_value(function, inflection_x)
            if inflection_y is not None:
                inflection_point = (inflection_x, inflection_y)
        return FunctionAnalysis(
            is_polynomial=True,
            degree=degree,
            x_intercepts=x_intercepts,
            y_intercept=y_intercept,
            vertex=vertex,
            slope=slope,
            concavity=concavity,
            symmetry_axis=symmetry_axis,
            inflection_point=inflection_point,
            is_zero_function=zero_function,
        )

    x_intercepts = None
    if (
        x_min is not None
        and x_max is not None
        and np.isfinite(x_min)
        and np.isfinite(x_max)
        and x_min < x_max
    ):
        try:
            x_intercepts = _numeric_roots(function, x_min, x_max)
        except (ArithmeticError, TypeError, ValueError, OverflowError):
            x_intercepts = None
    return FunctionAnalysis(False, None, x_intercepts, y_intercept, None)
