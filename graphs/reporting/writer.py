"""Reporting writer.

The writer composes a structured executive report from the research
and analytics results in the shared state. The implementation is
deterministic and template-based so the system can run end-to-end
without an LLM; production deployments can inject a custom writer
function.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from config.settings import ReportingConfig
from models.schemas import AnalyticsResult, ReportSection, ResearchFinding

if TYPE_CHECKING:
    from models.state import GraphState


_LOW_CONFIDENCE_THRESHOLD = 0.4
WriterFn = Callable[["GraphState", ReportingConfig], list[ReportSection]]


def default_writer(state: GraphState, config: ReportingConfig) -> list[ReportSection]:
    """Build a structured report from the state.

    The default writer produces five sections: Executive Summary,
    Findings, Analytics, Recommendations, and Appendix.
    """
    query = state.get("query", "")
    findings: list[ResearchFinding] = state.get("research_results", [])
    analytics: list[AnalyticsResult] = state.get("analytics_results", [])

    sections: list[ReportSection] = []

    summary_lines = [
        f"Objective: {query.strip() or 'unspecified'}.",
        f"Findings produced: {len(findings)}.",
        f"Analytics blocks produced: {len(analytics)}.",
    ]
    if config.review_enabled:
        summary_lines.append("Reviewer: enabled.")
    sections.append(
        ReportSection(
            heading="Executive Summary",
            body="\n".join(summary_lines),
            order=1,
        )
    )

    if findings:
        bullets = "\n".join(f"- {f.title} (confidence {f.confidence:.2f})" for f in findings)
        sections.append(ReportSection(heading="Findings", body=bullets, order=2))

    if analytics:
        kpi_lines: list[str] = []
        for block in analytics:
            for metric in block.kpis:
                kpi_lines.append(
                    f"- {metric.name}: {metric.value:.2f} {metric.unit}".strip()
                )
            for key, value in block.aggregations.items():
                kpi_lines.append(f"- {key}: {value:.4f}")
        if kpi_lines:
            sections.append(
                ReportSection(
                    heading="Analytics",
                    body="\n".join(kpi_lines) or "No analytics produced.",
                    order=3,
                )
            )

    recommendations = _derive_recommendations(findings, analytics)
    if recommendations:
        sections.append(
            ReportSection(heading="Recommendations", body=recommendations, order=4)
        )

    sections.append(
        ReportSection(
            heading="Appendix",
            body=f"Trace ID: {state.get('trace_id', 'n/a')}; Request ID: {state.get('request_id', 'n/a')}.",
            order=5,
        )
    )
    return sections


def _derive_recommendations(
    findings: list[ResearchFinding], analytics: list[AnalyticsResult]
) -> str:
    """Derive simple rule-based recommendations from the data."""
    recs: list[str] = []
    if not findings:
        recs.append("- Gather additional evidence before making decisions.")
    elif all(f.confidence < _LOW_CONFIDENCE_THRESHOLD for f in findings):
        recs.append("- Findings have low confidence; consider deeper research.")
    else:
        recs.append("- Validate the highest-confidence findings with domain experts.")

    if analytics and any(
        metric.trend == "down" for block in analytics for metric in block.kpis
    ):
        recs.append("- Investigate metrics with a downward trend.")

    if not recs:
        recs.append("- Continue monitoring; no anomalies detected.")  # pragma: no cover
    return "\n".join(recs)


def sections_to_text(sections: list[ReportSection]) -> str:
    """Render sections as a single text report."""
    ordered = sorted(sections, key=lambda s: s.order)
    parts: list[str] = []
    for section in ordered:
        parts.append(f"# {section.heading}\n{section.body}")
    return "\n\n".join(parts)


__all__ = ["WriterFn", "default_writer", "sections_to_text"]
