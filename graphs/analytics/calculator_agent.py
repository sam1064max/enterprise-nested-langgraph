"""Calculator agent.

The calculator agent is a thin orchestration layer that runs one or
more arithmetic expressions and aggregation calls. It uses the safe
evaluator from :mod:`tools.calculator` to avoid any ``eval``/``exec``
use in the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tools.calculator import CalculatorError, aggregate, safe_eval


@dataclass
class CalculationResult:
    """Outcome of a calculator agent invocation."""

    expression: str
    value: float
    error: str | None = None
    aggregations: dict[str, float] = field(default_factory=dict)


class CalculatorAgent:
    """Evaluate a list of arithmetic expressions and aggregations."""

    def __init__(self, variables: dict[str, float] | None = None) -> None:
        self._variables: dict[str, float] = dict(variables or {})

    def evaluate(
        self,
        expressions: list[str],
        aggregations: dict[str, list[float]] | None = None,
    ) -> list[CalculationResult]:
        """Evaluate each expression and aggregation.

        Args:
            expressions: Arithmetic expressions to evaluate.
            aggregations: Mapping of aggregate name to a list of values.

        Returns:
            One :class:`CalculationResult` per expression, in order.
        """
        results: list[CalculationResult] = []
        for expr in expressions:
            try:
                value = safe_eval(expr, self._variables)
                results.append(CalculationResult(expression=expr, value=value))
            except CalculatorError as exc:
                results.append(
                    CalculationResult(expression=expr, value=0.0, error=str(exc))
                )

        if aggregations:
            last = results[-1] if results else CalculationResult(expression="", value=0.0)
            for name, values in aggregations.items():
                try:
                    op = name.split(":")[1] if ":" in name else "sum"
                    last.aggregations[name] = aggregate(values, op=op)
                except CalculatorError as exc:
                    last.aggregations[name] = 0.0
                    last.error = str(exc)
        return results

    def to_records(self, results: list[CalculationResult]) -> list[dict[str, Any]]:
        """Convert results into a JSON-serializable list of dicts."""
        return [
            {
                "expression": r.expression,
                "value": r.value,
                "error": r.error,
                "aggregations": dict(r.aggregations),
            }
            for r in results
        ]


__all__ = ["CalculationResult", "CalculatorAgent"]
