"""Tests for the reporting subgraph."""

from __future__ import annotations

from config.settings import ReportingConfig
from graphs.reporting.graph import build_reporting_graph, run_reporting
from graphs.reporting.reviewer import review_report
from graphs.reporting.writer import default_writer, sections_to_text
from models.schemas import AnalyticsMetric, AnalyticsResult, ReportSection, ResearchFinding
from models.state import create_initial_state


def test_default_writer_produces_five_sections() -> None:
    state = create_initial_state("Analyze the market")
    state["research_results"] = [
        ResearchFinding(
            task_id="t1", title="Market growing", summary="10% YoY", confidence=0.7
        )
    ]
    state["analytics_results"] = [
        AnalyticsResult(
            kpis=[AnalyticsMetric(name="arr", value=1_000_000.0, unit="USD")],
            aggregations={"avg_arr": 1_000_000.0},
        )
    ]
    sections = default_writer(state, ReportingConfig())
    headings = {s.heading for s in sections}
    assert {"Executive Summary", "Findings", "Analytics", "Recommendations", "Appendix"} <= headings


def test_sections_to_text_preserves_order() -> None:
    sections = [
        ReportSection(heading="B", body="body B", order=2),
        ReportSection(heading="A", body="body A", order=1),
    ]
    text = sections_to_text(sections)
    assert text.index("# A") < text.index("# B")


def test_review_report_approves_well_formed_report() -> None:
    state = create_initial_state("q", request_id="r1", trace_id="t1")
    sections = [
        ReportSection(heading="Executive Summary", body="Summary r1 t1", order=1),
        ReportSection(heading="Findings", body="Findings r1 t1", order=2),
        ReportSection(heading="Analytics", body="Analytics r1 t1", order=3),
        ReportSection(heading="Recommendations", body="Recs r1 t1", order=4),
    ]
    review = review_report(sections, state, ReportingConfig())
    assert review.approved
    assert review.completeness_score == 1.0
    assert review.formatting_score == 1.0
    assert review.consistency_score == 1.0


def test_review_report_flags_missing_sections() -> None:
    state = create_initial_state("q", request_id="r1", trace_id="t1")
    sections = [ReportSection(heading="Executive Summary", body="x r1 t1", order=1)]
    review = review_report(sections, state, ReportingConfig())
    assert not review.approved
    assert review.completeness_score < 1.0


def test_review_disabled_short_circuits_to_approved() -> None:
    state = create_initial_state("q")
    review = review_report([], state, ReportingConfig(review_enabled=False))
    assert review.approved
    assert "disabled" in review.feedback


def test_reporting_graph_runs_end_to_end() -> None:
    state = create_initial_state("Analyze market")
    state["research_results"] = [
        ResearchFinding(task_id="t1", title="A", summary="a", confidence=0.6)
    ]
    state["analytics_results"] = [
        AnalyticsResult(kpis=[AnalyticsMetric(name="m", value=1.0)])
    ]
    graph = build_reporting_graph()
    result = graph.invoke(state)
    assert "Executive Summary" in result["report"]
    timings = result["metadata"]["subgraph_timings"]
    names = [t["name"] for t in timings]
    assert "reporting.writer" in names
    assert "reporting.reviewer" in names


def test_run_reporting_helper() -> None:
    state = create_initial_state("Generate report")
    state["research_results"] = [
        ResearchFinding(task_id="t", title="t", summary="s", confidence=0.5)
    ]
    result = run_reporting(state)
    assert "Executive Summary" in result["report"]


def test_review_accepts_on_final_pass_with_reservations() -> None:
    state = create_initial_state("q", request_id="r1", trace_id="t1")
    config = ReportingConfig(max_review_passes=2)
    sections = [
        ReportSection(heading="Executive Summary", body="x r1 t1", order=1),
        ReportSection(heading="Findings", body="y r1 t1", order=2),
    ]
    review = review_report(sections, state, config, pass_number=2)
    assert review.approved
    assert "reservations" in review.feedback
