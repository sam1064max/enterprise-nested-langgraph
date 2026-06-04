"""Tests for the supervisor graph."""

from __future__ import annotations

from graphs.supervisor.graph import build_supervisor_graph, run_supervisor
from models.state import create_initial_state


def test_supervisor_runs_all_subgraphs() -> None:
    state = create_initial_state("Analyze enterprise AI trends")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    assert result["research_results"], "research subgraph should produce findings"
    assert result["analytics_results"], "analytics subgraph should produce analytics"
    assert result["report"], "reporting subgraph should produce a report"
    assert result["status"] == "completed"
    timings = result["metadata"]["subgraph_timings"]
    names = {t["name"] for t in timings}
    # Each subgraph contributes its own timings; we just check the supervisor recorded them.
    assert "research.planner" in names
    assert "research.executor" in names
    assert "analytics.sql_agent" in names
    assert "analytics.calculator" in names
    assert "reporting.writer" in names
    assert "reporting.reviewer" in names


def test_run_supervisor_helper() -> None:
    state = create_initial_state("Test run")
    result = run_supervisor(state)
    assert result["report"]


def test_supervisor_finalize_computes_duration() -> None:
    state = create_initial_state("Compute duration")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    assert isinstance(result["execution_time"], float)
    assert result["execution_time"] >= 0.0
