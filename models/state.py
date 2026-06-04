"""LangGraph state definitions for the Enterprise Nested LangGraph system.

The state object is the contract passed between nodes in the supervisor
graph and its subgraphs. It is a ``TypedDict`` (not a Pydantic model)
because LangGraph requires a dict-like object for state updates and
reducers. The Pydantic schemas in :mod:`models.schemas` are used to
validate values written into the state via helper functions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, TypedDict
from uuid import uuid4

from models.schemas import AnalyticsResult, ResearchFinding, ResearchTask  # noqa: TC001


def _append(left: list[Any], right: Any) -> list[Any]:  # noqa: ANN401
    """Reducer that appends ``right`` to ``left``.

    LangGraph's reducers are invoked with the existing list as ``left``
    and the new value as ``right``. The new value may be a list (when
    the node returns a list) or a single item.
    """
    if isinstance(right, list):
        return [*left, *right]
    return [*left, right]


_APPEND_METADATA_KEYS = frozenset({"subgraph_timings", "state_transitions"})


def _merge_metadata(left: dict[str, Any], right: dict[str, Any] | None) -> dict[str, Any]:
    """Reducer that merges metadata dicts shallowly.

    For list-valued keys declared in :data:`_APPEND_METADATA_KEYS`
    (e.g. ``subgraph_timings`` and ``state_transitions``), values are
    appended to the existing list. All other keys are overwritten with
    the right-hand value.
    """
    if not right:
        return left
    merged: dict[str, Any] = {**left}
    for key, value in right.items():
        if key in _APPEND_METADATA_KEYS and isinstance(value, list):
            existing = merged.get(key, [])
            if isinstance(existing, list):
                merged[key] = [*existing, *value]
            else:
                merged[key] = value
        else:
            merged[key] = value
    return merged


class GraphState(TypedDict, total=False):
    """Top-level state shared across the supervisor and subgraphs.

    All fields are optional (``total=False``) so that subgraphs can
    produce partial state updates. Reducers are used to merge list
    and dict fields across subgraph executions.
    """

    query: str
    research_plan: list[ResearchTask]
    research_results: Annotated[list[ResearchFinding], _append]
    analytics_results: Annotated[list[AnalyticsResult], _append]
    report: str
    metadata: Annotated[dict[str, Any], _merge_metadata]
    error: str | None
    trace_id: str
    request_id: str
    execution_time: float
    status: str


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=timezone.utc)


def generate_id() -> str:
    """Generate a unique identifier."""
    return str(uuid4())


def create_initial_state(
    query: str,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> GraphState:
    """Build a fresh :class:`GraphState` for a new request.

    Args:
        query: The user's natural-language objective.
        request_id: Optional pre-generated request ID. A new one is
            generated if not provided.
        trace_id: Optional pre-generated trace ID. A new one is
            generated if not provided.

    Returns:
        A new state object ready to be passed into the supervisor graph.
    """
    return GraphState(
        query=query,
        research_plan=[],
        research_results=[],
        analytics_results=[],
        report="",
        metadata={
            "subgraph_timings": [],
            "state_transitions": [],
            "guardrail_violations": [],
            "started_at": utc_now().isoformat(),
        },
        error=None,
        trace_id=trace_id or generate_id(),
        request_id=request_id or generate_id(),
        execution_time=0.0,
        status="initialized",
    )


__all__ = [
    "GraphState",
    "create_initial_state",
    "generate_id",
    "utc_now",
]
