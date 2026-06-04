"""Tests for shared state models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.schemas import (
    AnalyticsMetric,
    AnalyticsResult,
    GuardrailViolation,
    ResearchFinding,
    ResearchTask,
    Severity,
    SubgraphTiming,
)
from models.state import create_initial_state, generate_id, utc_now


@pytest.fixture(autouse=True)
def _clear() -> None:
    return None


def test_research_task_validates_objective() -> None:
    task = ResearchTask(objective="Investigate the market")
    assert task.objective == "Investigate the market"
    assert task.priority == 1
    assert task.id  # auto-generated


def test_research_task_rejects_empty_objective() -> None:
    with pytest.raises(ValidationError, match="objective"):
        ResearchTask(objective="   ")


def test_research_task_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ResearchTask(objective="x", extra_field="oops")  # type: ignore[call-arg]


def test_research_finding_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        ResearchFinding(task_id="t1", title="t", summary="s", confidence=2.0)


def test_analytics_metric_value_can_be_negative() -> None:
    metric = AnalyticsMetric(name="delta", value=-12.5)
    assert metric.value == -12.5


def test_analytics_result_defaults() -> None:
    result = AnalyticsResult()
    assert result.kpis == []
    assert result.aggregations == {}
    assert result.sql_queries_executed == 0


def test_guardrail_violation_severity_enum() -> None:
    violation = GuardrailViolation(
        category="prompt_injection",
        pattern="ignore previous",
        severity=Severity.CRITICAL,
    )
    assert violation.severity is Severity.CRITICAL


def test_subgraph_timing_from_times() -> None:
    start = utc_now()
    end = start
    timing = SubgraphTiming.from_times("research", start, end)
    assert timing.name == "research"
    assert timing.duration_ms == 0.0


def test_create_initial_state_has_required_fields() -> None:
    state = create_initial_state("test query")
    assert state["query"] == "test query"
    assert state["research_results"] == []
    assert state["analytics_results"] == []
    assert state["report"] == ""
    assert state["error"] is None
    assert state["status"] == "initialized"
    assert "subgraph_timings" in state["metadata"]
    assert state["request_id"]
    assert state["trace_id"]


def test_create_initial_state_uses_provided_ids() -> None:
    state = create_initial_state("q", request_id="r1", trace_id="t1")
    assert state["request_id"] == "r1"
    assert state["trace_id"] == "t1"


def test_generate_id_is_unique() -> None:
    assert generate_id() != generate_id()
