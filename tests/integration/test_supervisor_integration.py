"""Integration tests for the supervisor + subgraphs end-to-end.

These tests exercise the full pipeline (research → analytics → reporting)
through the supervisor graph and assert that state flows correctly
through every node.
"""

from __future__ import annotations

from graphs.supervisor.graph import build_supervisor_graph, run_supervisor
from models.schemas import AnalyticsResult, ResearchFinding, ResearchTask
from models.state import create_initial_state


def test_supervisor_propagates_query_through_pipeline() -> None:
    query = "Investigate AI agent observability market dynamics"
    state = create_initial_state(query)
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    assert result["query"] == query


def test_supervisor_research_subgraph_emits_tasks() -> None:
    state = create_initial_state("Find three AI trends")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    plan = result["research_plan"]
    assert isinstance(plan, list)
    assert all(isinstance(task, ResearchTask) for task in plan)


def test_supervisor_research_subgraph_emits_findings() -> None:
    state = create_initial_state("Find three AI trends")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    findings = result["research_results"]
    assert findings
    assert all(isinstance(f, ResearchFinding) for f in findings)
    for finding in findings:
        assert finding.task_id
        assert finding.summary


def test_supervisor_analytics_subgraph_emits_results() -> None:
    state = create_initial_state("Compute analytics for AI market")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    analytics = result["analytics_results"]
    assert analytics
    assert all(isinstance(a, AnalyticsResult) for a in analytics)


def test_supervisor_reporting_subgraph_emits_report() -> None:
    state = create_initial_state("Produce a market report")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    report = result["report"]
    assert isinstance(report, str)
    assert "Executive Summary" in report
    assert "Recommendations" in report


def test_supervisor_metadata_records_state_transitions() -> None:
    state = create_initial_state("Trace the pipeline")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    transitions = result["metadata"].get("state_transitions", [])
    assert isinstance(transitions, list)
    assert len(transitions) >= 3


def test_supervisor_metadata_records_subgraph_timings() -> None:
    state = create_initial_state("Measure subgraph timings")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    timings = result["metadata"]["subgraph_timings"]
    assert timings
    for entry in timings:
        assert entry["name"]
        assert isinstance(entry["duration_ms"], float)
        assert entry["duration_ms"] >= 0.0


def test_supervisor_run_helper_returns_graph_state() -> None:
    state = create_initial_state("Run via helper")
    result = run_supervisor(state)
    assert result["status"] == "completed"
    assert result["report"]


def test_supervisor_status_transitions() -> None:
    state = create_initial_state("Check status flow")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    assert result["status"] == "completed"
    assert result["error"] is None


def test_supervisor_execution_time_is_non_negative() -> None:
    state = create_initial_state("Time the run")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    duration = result["execution_time"]
    assert isinstance(duration, float)
    assert duration >= 0.0


def test_supervisor_initial_state_has_request_and_trace_id() -> None:
    state = create_initial_state("Verify IDs")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    assert result["request_id"]
    assert result["trace_id"]


def test_supervisor_overrides_request_id_when_provided() -> None:
    state = create_initial_state("Custom ID", request_id="req-xyz")
    graph = build_supervisor_graph()
    result = graph.invoke(state)
    assert result["request_id"] == "req-xyz"
