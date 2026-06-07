"""Calculator tool.

A safe arithmetic expression evaluator used by the analytics subgraph.
The evaluator deliberately does **not** use Python's :func:`eval` or
:func:`exec`; it parses a small expression grammar (numbers, + - * /
** ( ) and named variables) using Python's :mod:`ast` module and
rejects anything else.
"""

from __future__ import annotations

import ast
import math
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


class CalculatorError(ValueError):
    """Raised when an expression cannot be evaluated safely."""


_BinaryOp = Callable[[float, float], float]
_UnaryOp = Callable[[float], float]

_UNARY_OPS: dict[type, _UnaryOp] = {
    ast.UAdd: lambda v: +v,
    ast.USub: lambda v: -v,
}

_BINARY_OPS: dict[type, _BinaryOp] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
}


def safe_eval(expression: str, variables: Mapping[str, float] | None = None) -> float:
    """Evaluate an arithmetic expression safely.

    Args:
        expression: A string containing a Python-like arithmetic
            expression. Only numbers, arithmetic operators, parentheses
            and variable names are allowed.
        variables: Optional mapping of variable names to values.

    Returns:
        The numeric result of the expression.

    Raises:
        CalculatorError: If the expression is empty, malformed, or
            uses unsupported nodes.
    """
    if not expression or not expression.strip():
        raise CalculatorError("expression must not be empty")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise CalculatorError(f"invalid expression: {exc.msg}") from exc

    resolved: dict[str, float] = dict(variables or {})
    return _evaluate(tree.body, resolved)


def _evaluate(node: ast.AST, variables: dict[str, float]) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int | float)):
            return float(node.value)
        raise CalculatorError(f"unsupported constant: {node.value!r}")

    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise CalculatorError(f"unknown variable: {node.id!r}")
        return float(variables[node.id])

    if isinstance(node, ast.BinOp):
        bin_op_type = type(node.op)
        binary_op = _BINARY_OPS.get(bin_op_type)
        if binary_op is None:
            raise CalculatorError(f"unsupported binary operator: {bin_op_type.__name__}")
        left = _evaluate(node.left, variables)
        right = _evaluate(node.right, variables)
        try:
            return binary_op(left, right)
        except ZeroDivisionError as exc:
            raise CalculatorError("division by zero") from exc

    if isinstance(node, ast.UnaryOp):
        un_op_type = type(node.op)
        unary_op = _UNARY_OPS.get(un_op_type)
        if unary_op is None:
            raise CalculatorError(f"unsupported unary operator: {un_op_type.__name__}")
        operand = _evaluate(node.operand, variables)
        return unary_op(operand)

    raise CalculatorError(f"unsupported node: {type(node).__name__}")


def aggregate(values: list[float], *, op: str = "sum") -> float:
    """Compute a simple aggregate over ``values``."""
    if not values:
        return 0.0
    if op == "sum":
        return float(sum(values))
    if op == "mean":
        return float(sum(values) / len(values))
    if op == "min":
        return float(min(values))
    if op == "max":
        return float(max(values))
    if op == "stdev":
        return _stdev(values)
    raise CalculatorError(f"unsupported aggregate op: {op!r}")


def _stdev(values: list[float]) -> float:
    """Return the sample standard deviation of ``values``."""
    if len(values) < _MIN_SAMPLE_FOR_STDEV:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return float(math.sqrt(variance))


_MIN_SAMPLE_FOR_STDEV = 2


__all__ = [
    "CalculatorError",
    "aggregate",
    "safe_eval",
]
