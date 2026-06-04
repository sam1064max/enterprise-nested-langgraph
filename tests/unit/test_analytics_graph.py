"""Tests for the analytics subgraph and supporting tools."""

from __future__ import annotations

import pytest

from config.settings import AnalyticsConfig
from graphs.analytics.calculator_agent import CalculatorAgent
from graphs.analytics.graph import build_analytics_graph, run_analytics
from graphs.analytics.sql_agent import SQLAgent
from models.state import create_initial_state
from tools.calculator import CalculatorError, aggregate, safe_eval


def test_safe_eval_supports_basic_arithmetic() -> None:
    assert safe_eval("1 + 2 * 3") == 7.0
    assert safe_eval("(1 + 2) * 3") == 9.0
    assert safe_eval("2 ** 8") == 256.0


def test_safe_eval_supports_variables() -> None:
    assert safe_eval("x * 2", {"x": 5}) == 10.0


def test_safe_eval_rejects_empty() -> None:
    with pytest.raises(CalculatorError, match="empty"):
        safe_eval("")


def test_safe_eval_rejects_unknown_variable() -> None:
    with pytest.raises(CalculatorError, match="unknown variable"):
        safe_eval("y + 1")


def test_safe_eval_rejects_unsafe_nodes() -> None:
    with pytest.raises(CalculatorError, match="unsupported"):
        safe_eval("__import__('os').system('echo hi')")


def test_safe_eval_division_by_zero() -> None:
    with pytest.raises(CalculatorError, match="division by zero"):
        safe_eval("1 / 0")


def test_aggregate_operations() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert aggregate(values, op="sum") == 10.0
    assert aggregate(values, op="mean") == 2.5
    assert aggregate(values, op="min") == 1.0
    assert aggregate(values, op="max") == 4.0
    assert aggregate(values, op="stdev") > 0


def test_aggregate_empty_returns_zero() -> None:
    assert aggregate([], op="sum") == 0.0


def test_sql_agent_runs_select() -> None:
    agent = SQLAgent()
    result = agent.run("SELECT plan, price_usd FROM plans ORDER BY price_usd")
    assert result.error is None
    assert result.row_count == 3
    assert result.columns == ["plan", "price_usd"]


def test_sql_agent_rejects_write_statements() -> None:
    agent = SQLAgent()
    result = agent.run("DELETE FROM plans")
    assert result.error is not None


def test_sql_agent_rejects_empty() -> None:
    agent = SQLAgent()
    result = agent.run("")
    assert result.error == "empty query"


def test_calculator_agent_handles_errors() -> None:
    agent = CalculatorAgent()
    results = agent.evaluate(["1 + 1", "x + 1"])
    assert results[0].value == 2.0
    assert results[1].error is not None


def test_calculator_agent_aggregations() -> None:
    agent = CalculatorAgent({"avg_arr": 1_000_000.0})
    results = agent.evaluate(
        ["avg_arr * 12"],
        aggregations={"stat:mean": [1.0, 2.0, 3.0]},
    )
    assert results[0].value == 12_000_000.0
    assert results[0].aggregations["stat:mean"] == 2.0


def test_analytics_graph_runs_end_to_end() -> None:
    state = create_initial_state("Analyze SaaS KPIs")
    graph = build_analytics_graph(config=AnalyticsConfig())
    result = graph.invoke(state)
    assert len(result["analytics_results"]) >= 1
    timings = result["metadata"]["subgraph_timings"]
    names = [t["name"] for t in timings]
    assert "analytics.sql_agent" in names
    assert "analytics.calculator" in names


def test_run_analytics_helper() -> None:
    state = create_initial_state("Analyze revenue")
    result = run_analytics(state)
    assert result["analytics_results"]


def test_analytics_graph_with_disabled_calculations() -> None:
    state = create_initial_state("Analyze")
    config = AnalyticsConfig(calculations_enabled=False, sql_enabled=False)
    graph = build_analytics_graph(config=config)
    result = graph.invoke(state)
    # Even when disabled, both nodes should still emit analytics entries.
    assert len(result["analytics_results"]) >= 1
    notes = [r.notes for r in result["analytics_results"]]
    assert "disabled" in notes
