"""Parse a restricted mathematical expression into a callable function."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any

import numpy as np

from .functions import BINARY_OPERATORS, CONSTANTS, FUNCTIONS, UNARY_OPERATORS


class ExpressionError(ValueError):
    """Raised when an expression is not in the supported math grammar."""


_TOKEN_PATTERN = re.compile(
    r"\s*(?:(?P<number>(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"|(?P<name>[A-Za-z_]\w*)|(?P<operator>[+\-*/%^(),]))"
)


def _normalize_expression(expression: str) -> str:
    normalized = expression.replace("×", "*").replace("÷", "/").replace("^", "**")
    tokens: list[tuple[str, str]] = []
    position = 0

    while position < len(normalized):
        match = _TOKEN_PATTERN.match(normalized, position)
        if match is None:
            if normalized[position:].strip() == "":
                break
            raise ExpressionError(f"Carácter no permitido cerca de: {normalized[position:position + 8]!r}")
        kind = "number" if match.group("number") is not None else (
            "name" if match.group("name") is not None else "operator"
        )
        value = match.group(kind).lower() if kind == "name" else match.group(kind)
        tokens.append((kind, value))
        position = match.end()

    if not tokens:
        raise ExpressionError("Escribe una función antes de graficar.")

    expanded: list[str] = []
    previous: tuple[str, str] | None = None
    for token in tokens:
        kind, value = token
        if previous is not None:
            left_kind, left_value = previous
            left_is_atom = (
                left_kind == "number"
                or left_value == ")"
                or (left_kind == "name" and left_value in {"x", "e", "pi"})
            )
            right_is_atom = kind == "number" or kind == "name" or value == "("
            is_function_call = left_kind == "name" and left_value in FUNCTIONS and value == "("
            if left_is_atom and right_is_atom and not is_function_call:
                expanded.append("*")
        expanded.append(value)
        previous = token

    return "".join(expanded)


def _evaluate_node(node: ast.AST, x: Any) -> Any:
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body, x)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name):
        if node.id == "x":
            return x
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise ExpressionError(f"Nombre no reconocido: {node.id}")
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPERATORS:
        left = _evaluate_node(node.left, x)
        right = _evaluate_node(node.right, x)
        return BINARY_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPERATORS:
        return UNARY_OPERATORS[type(node.op)](_evaluate_node(node.operand, x))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        function = FUNCTIONS.get(node.func.id)
        if function is None:
            raise ExpressionError(f"Función no reconocida: {node.func.id}")
        allowed_arguments = (1, 2) if node.func.id == "log" else (1,)
        if len(node.args) not in allowed_arguments or node.keywords:
            raise ExpressionError(f"Número de argumentos inválido para {node.func.id}().")
        arguments = [_evaluate_node(argument, x) for argument in node.args]
        return function(*arguments)
    raise ExpressionError("La expresión contiene una operación no permitida.")


@dataclass(frozen=True)
class ParsedFunction:
    """A validated expression that can be evaluated for scalar or array x values."""

    expression: str
    _tree: ast.Expression

    def __call__(self, x: Any) -> Any:
        with np.errstate(all="ignore"):
            return _evaluate_node(self._tree, x)


def parse_function(expression: str) -> ParsedFunction:
    """Compile polynomial, exponential, logarithmic, and common math expressions."""
    normalized = _normalize_expression(expression.strip())
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as error:
        raise ExpressionError("La expresión no tiene un formato matemático válido.") from error

    parsed = ParsedFunction(expression.strip(), tree)
    parsed(np.array([1.0]))
    return parsed