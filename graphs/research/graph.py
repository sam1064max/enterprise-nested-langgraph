"""Research subgraph.

This module builds a LangGraph :class:`StateGraph` representing the
research workflow. The graph is a 2-node pipeline:

    START -> planner -> executor -> END

The planner produces a list of :class:`ResearchTask` objects which
are stored in ``research_plan``. The executor consumes the plan and
produces ``research_results``. Both nodes update shared state via
LangGraph reducers defined in :mod:`models.state`.

The search client and planner function are injected at graph build
time so the same code can be exercised against mocks in tests and
real services in production.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from config.settings import ResearchConfig
from graphs.research.executor import execute_plan
from graphs.research.planner import PlannerFn, heuristic_planner
from models.schemas import SubgraphTiming
from models.state import GraphState, utc_now
from tools.search import InMemorySearchClient, SearchClient


def _planner_node(
    state: GraphState,
    *,
    planner_fn: PlannerFn,
    config: ResearchConfig,
) -> dict:
    """Plan node: decompose the objective into research tasks."""
    query = state.get("query", "")
    started = utc_now()
    tasks = planner_fn(query, config)
    finished = utc_now()
    timing = SubgraphTiming.from_times("research.planner", started, finished)
    return {
        "research_plan": tasks,
        "metadata": {
            "subgraph_timings": [timing.model_dump()],
            "state_transitions": [
                {
                    "node": "research.planner",
                    "at": finished.isoformat(),
                    "tasks": [t.model_dump() for t in tasks],
                }
            ],
        },
    }


def _executor_node(
    state: GraphState,
    *,
    client: SearchClient,
    config: ResearchConfig,
) -> dict:
    """Executor node: run the plan and collect findings."""
    started = utc_now()
    tasks = state.get("research_plan", [])
    findings = execute_plan(tasks, client, config)
    finished = utc_now()
    timing = SubgraphTiming.from_times("research.executor", started, finished)
    return {
        "research_results": findings,
        "metadata": {
            "subgraph_timings": [timing.model_dump()],
            "state_transitions": [
                {
                    "node": "research.executor",
                    "at": finished.isoformat(),
                    "findings": [f.model_dump() for f in findings],
                }
            ],
        },
    }


def build_research_graph(
    *,
    client: SearchClient | None = None,
    planner_fn: PlannerFn | None = None,
    config: ResearchConfig | None = None,
) -> Any:  # noqa: ANN401
    """Build the research subgraph.

    Args:
        client: Optional search client. Defaults to
            :class:`InMemorySearchClient` for tests and demos.
        planner_fn: Optional planner function. Defaults to
            :func:`heuristic_planner`.
        config: Research configuration. Defaults to a fresh
            :class:`ResearchConfig` instance.
    """
    if client is None:
        client = InMemorySearchClient()
    if planner_fn is None:
        planner_fn = heuristic_planner
    if config is None:
        config = ResearchConfig()

    graph: StateGraph = StateGraph(GraphState)

    graph.add_node(
        "planner",
        lambda state: _planner_node(state, planner_fn=planner_fn, config=config),
    )
    graph.add_node(
        "executor",
        lambda state: _executor_node(state, client=client, config=config),
    )
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", END)
    return graph.compile()


def run_research(
    state: GraphState,
    *,
    client: SearchClient | None = None,
    planner_fn: PlannerFn | None = None,
    config: ResearchConfig | None = None,
) -> dict[str, Any]:
    """Invoke the research subgraph against a state object."""
    graph = build_research_graph(client=client, planner_fn=planner_fn, config=config)
    result: dict[str, Any] = graph.invoke(state)
    return result


__all__ = [
    "build_research_graph",
    "run_research",
]
