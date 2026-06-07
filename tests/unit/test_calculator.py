"""Tests for the safe calculator."""

from __future__ import annotations

import pytest

from tools.calculator import CalculatorError, aggregate, safe_eval


def test_safe_eval_simple_arithmetic() -> None:
    assert safe_eval("1 + 1", {}) == 2.0
    assert safe_eval("10 - 3", {}) == 7.0
    assert safe_eval("4 * 5", {}) == 20.0
    assert safe_eval("8 / 2", {}) == 4.0


def test_safe_eval_unary_operators() -> None:
    assert safe_eval("-5", {}) == -5.0
    assert safe_eval("+5", {}) == 5.0


def test_safe_eval_power() -> None:
    assert safe_eval("2 ** 8", {}) == 256.0


def test_safe_eval_parentheses() -> None:
    assert safe_eval("(1 + 2) * 3", {}) == 9.0
    assert safe_eval("((10 - 2) / 2) ** 2", {}) == 16.0


def test_safe_eval_with_variables() -> None:
    assert safe_eval("a + b", {"a": 2.0, "b": 3.0}) == 5.0
    assert safe_eval("x * y - z", {"x": 2.0, "y": 3.0, "z": 1.0}) == 5.0


def test_safe_eval_floor_division_and_modulo() -> None:
    assert safe_eval("7 // 2", {}) == 3.0
    assert safe_eval("7 % 3", {}) == 1.0


def test_safe_eval_rejects_division_by_zero() -> None:
    with pytest.raises(CalculatorError):
        safe_eval("1 / 0", {})


def test_safe_eval_rejects_invalid_syntax() -> None:
    with pytest.raises(CalculatorError):
        safe_eval("1 +", {})


def test_safe_eval_rejects_function_calls() -> None:
    with pytest.raises(CalculatorError):
        safe_eval("abs(-1)", {})


def test_safe_eval_rejects_name_lookup() -> None:
    with pytest.raises(CalculatorError):
        safe_eval("__import__('os').system('echo pwned')", {})


def test_safe_eval_rejects_strings() -> None:
    with pytest.raises(CalculatorError):
        safe_eval("'hello'", {})


def test_safe_eval_rejects_unsupported_node() -> None:
    with pytest.raises(CalculatorError):
        safe_eval("[1, 2, 3]", {})


def test_aggregate_sum() -> None:
    assert aggregate([1.0, 2.0, 3.0], op="sum") == 6.0


def test_aggregate_mean() -> None:
    assert aggregate([2.0, 4.0, 6.0], op="mean") == 4.0


def test_aggregate_min_max() -> None:
    assert aggregate([3.0, 1.0, 2.0], op="min") == 1.0
    assert aggregate([3.0, 1.0, 2.0], op="max") == 3.0


def test_aggregate_stdev() -> None:
    result = aggregate([1.0, 2.0, 3.0, 4.0, 5.0], op="stdev")
    assert result == pytest.approx(1.5811, abs=0.001)


def test_aggregate_empty_returns_zero() -> None:
    assert aggregate([], op="sum") == 0.0


def test_aggregate_stdev_single_returns_zero() -> None:
    assert aggregate([5.0], op="stdev") == 0.0


def test_aggregate_unknown_op_raises() -> None:
    with pytest.raises(CalculatorError):
        aggregate([1.0, 2.0], op="median")
