"""Vectorized mathematical functions and operators for expression evaluation."""

from __future__ import annotations

import ast
import operator
from typing import Callable

import numpy as np


def _log(value: object, base: object | None = None) -> object:
    if base is None:
        return np.log10(value)
    return np.log(value) / np.log(base)


FUNCTIONS: dict[str, Callable[..., object]] = {
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "asin": np.arcsin,
    "acos": np.arccos,
    "atan": np.arctan,
    "sinh": np.sinh,
    "cosh": np.cosh,
    "tanh": np.tanh,
    "exp": np.exp,
    "ln": np.log,
    "log": _log,
    "log10": np.log10,
    "log2": np.log2,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "floor": np.floor,
    "ceil": np.ceil,
}

CONSTANTS: dict[str, float] = {"pi": float(np.pi), "e": float(np.e)}

BINARY_OPERATORS: dict[type[ast.operator], Callable[[object, object], object]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[object], object]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}