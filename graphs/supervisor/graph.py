"""Supervisor graph.

The supervisor orchestrates the research, analytics, and reporting
subgraphs. It uses LangGraph's ``add_node`` API to register each
subgraph as a node and runs them sequentially with shared state.

Pipeline:

    START
      -> research
        -> analytics
          -> reporting
            -> finalize -> END
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

from config.settings import get_settings
from graphs.analytics.graph import build_analytics_graph
from graphs.reporting.graph import build_reporting_graph
from graphs.research.graph import build_research_graph
from models.schemas import SubgraphTiming
from models.state import GraphState, utc_now


def _record_timing(name: str, started: datetime, finished: datetime) -> dict[str, Any]:
    timing = SubgraphTiming.from_times(name, started, finished)
    return {
        "metadata": {
            "subgraph_timings": [timing.model_dump()],
            "state_transitions": [
                {
                    "node": f"supervisor.{name}",
                    "at": finished.isoformat(),
                }
            ],
        }
    }


def _supervisor_research(state: GraphState) -> dict[str, Any]:
    settings = get_settings()
    started = utc_now()
    subgraph = build_research_graph(config=settings.research)
    result: dict[str, Any] = subgraph.invoke(state)
    finished = utc_now()
    update = _record_timing("research", started, finished)
    update["research_plan"] = result.get("research_plan", [])
    update["research_results"] = result.get("research_results", [])
    update["metadata"] = {
        **update["metadata"],
        **result.get("metadata", {}),
    }
    return update


def _supervisor_analytics(state: GraphState) -> dict[str, Any]:
    settings = get_settings()
    started = utc_now()
    subgraph = build_analytics_graph(config=settings.analytics)
    result = subgraph.invoke(state)
    finished = utc_now()
    update = _record_timing("analytics", started, finished)
    update["analytics_results"] = result.get("analytics_results", [])
    update["metadata"] = {
        **update["metadata"],
        **result.get("metadata", {}),
    }
    return update


def _supervisor_reporting(state: GraphState) -> dict[str, Any]:
    settings = get_settings()
    started = utc_now()
    subgraph = build_reporting_graph(config=settings.reporting)
    result = subgraph.invoke(state)
    finished = utc_now()
    update = _record_timing("reporting", started, finished)
    update["report"] = result.get("report", "")
    update["metadata"] = {
        **update["metadata"],
        **result.get("metadata", {}),
    }
    return update


def _finalize(state: GraphState) -> dict[str, Any]:
    finished = utc_now()
    started_iso = state.get("metadata", {}).get("started_at")
    duration = 0.0
    if isinstance(started_iso, str):
        try:
            started_dt = datetime.fromisoformat(started_iso)
            duration = (finished - started_dt).total_seconds()
        except ValueError:
            duration = 0.0
    return {
        "execution_time": duration,
        "status": "completed" if not state.get("error") else "completed_with_errors",
        "metadata": {
            "state_transitions": [
                {"node": "supervisor.finalize", "at": finished.isoformat()}
            ],
        },
    }


def build_supervisor_graph() -> Any:  # noqa: ANN401
    """Build the top-level supervisor graph.

    The supervisor composes the three subgraphs and adds a finalize
    node that computes the total execution time.
    """
    graph: StateGraph = StateGraph(GraphState)
    graph.add_node("research", _supervisor_research)
    graph.add_node("analytics", _supervisor_analytics)
    graph.add_node("reporting", _supervisor_reporting)
    graph.add_node("finalize", _finalize)
    graph.add_edge(START, "research")
    graph.add_edge("research", "analytics")
    graph.add_edge("analytics", "reporting")
    graph.add_edge("reporting", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def run_supervisor(state: GraphState) -> dict[str, Any]:
    """Invoke the supervisor against a state object."""
    graph = build_supervisor_graph()
    result: dict[str, Any] = graph.invoke(state)
    return result


__all__ = ["build_supervisor_graph", "run_supervisor"]
