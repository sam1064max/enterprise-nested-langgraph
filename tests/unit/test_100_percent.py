"""Tests targeting the final uncovered lines to bring coverage to 100%.

Each test in this file is intentionally focused on a single uncovered
branch or line reported by ``pytest --cov``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

from config.settings import _YamlSettingsSource, reload_settings_from_path
from graphs.analytics.calculator_agent import CalculationResult, CalculatorAgent
from graphs.analytics.graph import _calculator_node, _sql_node, build_analytics_graph
from graphs.reporting.graph import _reviewer_node, build_reporting_graph
from graphs.reporting.reviewer import _score_completeness, _score_formatting
from graphs.reporting.writer import _derive_recommendations, default_writer
from graphs.research.graph import build_research_graph
from graphs.research.planner import heuristic_planner
from graphs.supervisor.graph import _finalize
from models.schemas import AnalyticsResult
from models.state import GraphState, _merge_metadata

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# config/settings.py:164  (yaml_path does not exist)
# ---------------------------------------------------------------------------


def test_yaml_settings_source_returns_empty_when_file_missing(tmp_path: Path) -> None:
    reload_settings_from_path(tmp_path / "nonexistent.yaml")
    try:
        source = _YamlSettingsSource(MagicMock())
        data = source()
        assert data == {}
    finally:
        reload_settings_from_path(Path("config/config.yaml"))


# ---------------------------------------------------------------------------
# graphs/analytics/graph.py:57-58 (non-numeric value in AVG row)
# ---------------------------------------------------------------------------


def test_sql_node_skips_non_numeric_aggregations() -> None:
    """When the AVG(arr) row has a non-numeric value, it is skipped."""
    from config.settings import AnalyticsConfig

    fake_result = MagicMock()
    fake_result.error = None
    fake_result.rows = [("not_a_number",)]
    fake_result.columns = ["avg_arr"]

    agent = MagicMock()
    agent.run.return_value = fake_result

    config = AnalyticsConfig()
    result = _sql_node({"query": "x"}, agent=agent, config=config)
    analytics = result["analytics_results"][0]
    assert analytics.aggregations == {}


# ---------------------------------------------------------------------------
# graphs/analytics/graph.py:105 (calculator error)
# ---------------------------------------------------------------------------


def test_calculator_node_skips_error_results() -> None:
    """Calculator error path in _calculator_node."""
    from config.settings import AnalyticsConfig
    from graphs.analytics import graph as analytics_graph
    from graphs.analytics.calculator_agent import CalculationResult

    config = AnalyticsConfig()
    state = {
        "analytics_results": [
            AnalyticsResult(aggregations={"avg_arr": 100.0, "avg_churn": 2.0}),
        ],
    }

    class _FailingAgent:
        def __init__(self, variables: dict[str, float] | None = None) -> None:
            pass

        def evaluate(self, expressions: list[str]) -> list[CalculationResult]:
            return [
                CalculationResult(expression="avg_arr * 12", value=0.0, error="boom"),
                CalculationResult(
                    expression="avg_arr * (1 - avg_churn / 100)",
                    value=0.0,
                    error="boom",
                ),
            ]

    original = analytics_graph.CalculatorAgent
    analytics_graph.CalculatorAgent = _FailingAgent  # type: ignore[assignment,misc]
    try:
        result = _calculator_node(state, agent=CalculatorAgent(), config=config)  # type: ignore[arg-type]
    finally:
        analytics_graph.CalculatorAgent = original  # type: ignore[misc]

    analytics = result["analytics_results"][-1]
    assert analytics.kpis == []


# ---------------------------------------------------------------------------
# graphs/analytics/graph.py:156->158, 158->160 (default agents)
# ---------------------------------------------------------------------------


def test_build_analytics_graph_uses_default_agents() -> None:
    graph = build_analytics_graph()
    assert graph is not None


def test_build_analytics_graph_with_explicit_agents() -> None:
    """Call with explicit agents to cover the False branches of the defaults."""
    from graphs.analytics.calculator_agent import CalculatorAgent
    from graphs.analytics.sql_agent import SQLAgent

    sql_agent = SQLAgent()
    calc_agent = CalculatorAgent()
    graph = build_analytics_graph(sql_agent=sql_agent, calculator_agent=calc_agent)
    assert graph is not None


# ---------------------------------------------------------------------------
# graphs/reporting/graph.py:82 (reviewer not approved at non-final pass)
# ---------------------------------------------------------------------------


def test_reviewer_node_sets_error_when_not_approved() -> None:
    from config.settings import ReportingConfig

    # Build a report that fails completeness (no recommended sections)
    # and pass_number=1 with max_review_passes=2, so the not-approved
    # branch is taken.
    report = "# Other\nbody content"
    config = ReportingConfig(review_enabled=True, max_review_passes=2)
    state = cast(
        GraphState,
        {
            "report": report,
            "metadata": {"review_pass": 0},
        },
    )
    result = _reviewer_node(state, config=config)
    assert result.get("error")


# ---------------------------------------------------------------------------
# graphs/reporting/graph.py:110->112 (default writer_fn)
# ---------------------------------------------------------------------------


def test_build_reporting_graph_uses_default_writer() -> None:
    graph = build_reporting_graph()
    assert graph is not None


def test_build_reporting_graph_with_explicit_writer() -> None:
    """Call with an explicit writer_fn to cover the False branch of the default."""
    from graphs.reporting.writer import default_writer

    graph = build_reporting_graph(writer_fn=default_writer)
    assert graph is not None


# ---------------------------------------------------------------------------
# graphs/reporting/reviewer.py:93, 100
# ---------------------------------------------------------------------------


def test_score_completeness_with_empty_sections() -> None:
    assert _score_completeness([]) == 0.0


def test_score_formatting_with_empty_sections() -> None:
    assert _score_formatting([]) == 0.0


# ---------------------------------------------------------------------------
# graphs/reporting/writer.py:66->75, 76->81, 109
# ---------------------------------------------------------------------------


def test_writer_skips_analytics_section_when_no_kpis() -> None:
    """`if kpi_lines:` is False when there are no kpis or aggregations."""
    from config.settings import ReportingConfig
    from models.schemas import ResearchFinding

    config = ReportingConfig()
    findings = [ResearchFinding(task_id="t", title="t", summary="s", source="x", confidence=0.9)]
    # Analytics block with no kpis and no aggregations → kpi_lines is empty
    analytics = [AnalyticsResult()]
    sections = default_writer(
        {"query": "x", "research_results": findings, "analytics_results": analytics},
        config,
    )
    headings = [s.heading for s in sections]
    assert "Analytics" not in headings


def test_writer_skips_recommendations_when_empty() -> None:
    """`if recommendations:` is False when _derive_recommendations returns empty."""
    # _derive_recommendations never returns empty (it always appends
    # something), so to exercise this branch we monkeypatch it.
    import graphs.reporting.writer as writer_module

    def _empty(_f: Any, _a: Any) -> str:
        return ""

    original = writer_module._derive_recommendations
    writer_module._derive_recommendations = _empty  # type: ignore[assignment]
    try:
        from config.settings import ReportingConfig

        config = ReportingConfig()
        sections = default_writer({"query": "x"}, config)
        headings = [s.heading for s in sections]
        assert "Recommendations" not in headings
    finally:
        writer_module._derive_recommendations = original


def test_derive_recommendations_default_branch() -> None:
    """The default `Validate the highest-confidence` branch is exercised."""
    from models.schemas import ResearchFinding

    findings = [ResearchFinding(task_id="t", title="t", summary="s", source="x", confidence=0.9)]
    text = _derive_recommendations(findings, [])
    assert "Validate the highest-confidence" in text


# ---------------------------------------------------------------------------
# graphs/research/graph.py:104->106
# ---------------------------------------------------------------------------


def test_build_research_graph_uses_default_planner() -> None:
    graph = build_research_graph()
    assert graph is not None


def test_build_research_graph_with_explicit_planner() -> None:
    """Call with an explicit planner_fn to cover the False branch of the default."""
    from graphs.research.planner import heuristic_planner

    graph = build_research_graph(planner_fn=heuristic_planner)
    assert graph is not None


# ---------------------------------------------------------------------------
# graphs/research/planner.py:39 (skip empty objective after split)
# ---------------------------------------------------------------------------


def test_planner_skips_empty_objective_after_strip() -> None:
    """When a segment strips to empty, the planner must skip it."""
    from config.settings import ResearchConfig

    config = ResearchConfig(dedupe_results=False, max_steps=5)
    # "find trends. . summarize risks" has a "." segment that strips to ""
    tasks = heuristic_planner("find trends. . summarize risks", config)
    objectives = [t.objective for t in tasks]
    assert "" not in objectives


# ---------------------------------------------------------------------------
# graphs/supervisor/graph.py:96->102
# ---------------------------------------------------------------------------


def test_finalize_with_valid_iso_string_computes_duration() -> None:
    started = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    state = cast(
        GraphState,
        {"metadata": {"started_at": started}, "error": None},
    )
    result = _finalize(state)
    assert isinstance(result["execution_time"], float)


def test_finalize_with_non_string_started_at() -> None:
    """When started_at is not a string (e.g. None or dict), duration stays 0."""
    non_string_values: list[object] = [None, 0, [], {}, 42]
    for non_string in non_string_values:
        state = cast(
            GraphState,
            {"metadata": {"started_at": non_string}, "error": None},
        )
        result = _finalize(state)
        assert result["execution_time"] == 0.0


# ---------------------------------------------------------------------------
# models/state.py:51 (non-list existing value in merge_metadata)
# ---------------------------------------------------------------------------


def test_merge_metadata_with_non_list_existing_appends() -> None:
    """When existing value is a list-typed metadata key but not actually a list."""
    # Use a key in _APPEND_METADATA_KEYS so we enter the list-appending branch,
    # then provide a non-list existing value to exercise the else branch.
    merged = _merge_metadata(
        {"subgraph_timings": "old_scalar"},
        {"subgraph_timings": [{"name": "new"}]},
    )
    assert merged["subgraph_timings"] == [{"name": "new"}]
