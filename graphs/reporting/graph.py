"""Reporting subgraph.

Pipeline:

    START -> writer -> reviewer -> END

The writer composes a structured report from the research and
analytics results. The reviewer validates completeness, formatting,
and consistency, and may request revisions (up to ``max_review_passes``
times). The reviewer is enabled by ``reporting.review_enabled`` in
the configuration.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from config.settings import ReportingConfig
from graphs.reporting.reviewer import review_report
from graphs.reporting.writer import WriterFn, default_writer, sections_to_text
from models.schemas import ReportSection, SubgraphTiming
from models.state import GraphState, utc_now


def _writer_node(
    state: GraphState,
    *,
    writer_fn: WriterFn,
    config: ReportingConfig,
) -> dict[str, Any]:
    """Compose the report sections."""
    started = utc_now()
    sections = writer_fn(state, config)
    text = sections_to_text(sections)
    finished = utc_now()
    timing = SubgraphTiming.from_times("reporting.writer", started, finished)
    return {
        "report": text,
        "metadata": {
            "subgraph_timings": [timing.model_dump()],
            "state_transitions": [
                {
                    "node": "reporting.writer",
                    "at": finished.isoformat(),
                    "section_count": len(sections),
                }
            ],
        },
    }


def _reviewer_node(
    state: GraphState,
    *,
    config: ReportingConfig,
) -> dict[str, Any]:
    """Run the reviewer against the current report."""
    started = utc_now()
    sections = _parse_sections(state.get("report", ""))
    pass_number = int(state.get("metadata", {}).get("review_pass", 0)) + 1
    review = review_report(sections, state, config, pass_number=pass_number)
    finished = utc_now()
    timing = SubgraphTiming.from_times("reporting.reviewer", started, finished)
    new_state: dict[str, Any] = {
        "metadata": {
            "subgraph_timings": [timing.model_dump()],
            "state_transitions": [
                {
                    "node": "reporting.reviewer",
                    "at": finished.isoformat(),
                    "approved": review.approved,
                    "pass_number": review.pass_number,
                }
            ],
            "last_review": review.model_dump(),
            "review_pass": pass_number,
        }
    }
    if not review.approved and pass_number < config.max_review_passes:
        new_state["error"] = review.feedback
    return new_state


def _parse_sections(report: str) -> list[ReportSection]:
    """Parse a rendered report back into sections (best effort)."""
    sections: list[ReportSection] = []
    order = 0
    for raw_chunk in report.split("\n\n"):
        chunk = raw_chunk.strip()
        if not chunk:
            continue
        order += 1
        if chunk.startswith("# "):
            heading = chunk[2:].split("\n", 1)[0].strip()
            body = "\n".join(chunk.split("\n")[1:]).strip()
            sections.append(ReportSection(heading=heading, body=body, order=order))
        else:
            sections.append(ReportSection(heading="", body=chunk, order=order))
    return sections


def build_reporting_graph(
    *,
    writer_fn: WriterFn | None = None,
    config: ReportingConfig | None = None,
) -> Any:  # noqa: ANN401
    """Build the reporting subgraph."""
    if writer_fn is None:
        writer_fn = default_writer
    if config is None:
        config = ReportingConfig()

    graph: StateGraph = StateGraph(GraphState)
    graph.add_node(
        "writer",
        lambda state: _writer_node(state, writer_fn=writer_fn, config=config),
    )
    graph.add_node(
        "reviewer",
        lambda state: _reviewer_node(state, config=config),
    )
    graph.add_edge(START, "writer")
    graph.add_edge("writer", "reviewer")
    graph.add_edge("reviewer", END)
    return graph.compile()


def run_reporting(
    state: GraphState,
    *,
    writer_fn: WriterFn | None = None,
    config: ReportingConfig | None = None,
) -> dict[str, Any]:
    """Invoke the reporting subgraph against a state object."""
    graph = build_reporting_graph(writer_fn=writer_fn, config=config)
    result: dict[str, Any] = graph.invoke(state)
    return result


__all__ = ["build_reporting_graph", "run_reporting"]
