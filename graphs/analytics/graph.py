"""Analytics subgraph.

Pipeline:

    START -> sql_agent -> calculator -> END

The SQL agent runs a small set of predefined analytics queries
against the in-memory dataset. The calculator agent derives additional
metrics (e.g. growth, totals) from those results. Both nodes write to
``analytics_results`` via the LangGraph reducer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.graph import END, START, StateGraph

from config.settings import AnalyticsConfig
from graphs.analytics.calculator_agent import CalculatorAgent
from graphs.analytics.sql_agent import SQLAgent
from models.schemas import AnalyticsMetric, AnalyticsResult, SubgraphTiming
from models.state import GraphState, utc_now

if TYPE_CHECKING:
    from datetime import datetime


_DEFAULT_QUERIES: tuple[str, ...] = (
    "SELECT month, arr, customers, logo_churn_pct FROM monthly_arr ORDER BY month",
    "SELECT AVG(arr) AS avg_arr, AVG(logo_churn_pct) AS avg_churn FROM monthly_arr",
    "SELECT plan, price_usd, seats FROM plans ORDER BY price_usd DESC",
)


def _sql_node(state: GraphState, *, agent: SQLAgent, config: AnalyticsConfig) -> dict[str, Any]:
    """Run the predefined SQL queries and aggregate results."""
    _ = state
    started = utc_now()
    if not config.sql_enabled:
        return _no_op_result("analytics.sql_agent", started, disabled=True)

    aggregations: dict[str, float] = {}
    notes_parts: list[str] = []
    executed = 0
    for query in _DEFAULT_QUERIES:
        result = agent.run(query)
        executed += 1
        if result.error:
            notes_parts.append(f"query failed: {result.error}")
            continue
        if "AVG(arr)" in query:
            row = result.rows[0] if result.rows else ()
            for column, value in zip(result.columns, row, strict=False):
                try:
                    aggregations[column] = float(value)
                except (TypeError, ValueError):
                    continue

    finished = utc_now()
    timing = SubgraphTiming.from_times("analytics.sql_agent", started, finished)
    analytics = AnalyticsResult(
        aggregations=aggregations,
        sql_queries_executed=executed,
        notes="; ".join(notes_parts),
    )
    return {
        "analytics_results": [analytics],
        "metadata": {
            "subgraph_timings": [timing.model_dump()],
            "state_transitions": [
                {"node": "analytics.sql_agent", "at": finished.isoformat()}
            ],
        },
    }


def _calculator_node(
    state: GraphState,
    *,
    agent: CalculatorAgent,
    config: AnalyticsConfig,
) -> dict[str, Any]:
    """Compute derived metrics from the previous node's aggregations."""
    _ = agent
    started = utc_now()
    if not config.calculations_enabled:
        return _no_op_result("analytics.calculator", started, disabled=True)

    aggregations: dict[str, float] = {}
    for entry in state.get("analytics_results", []):
        aggregations.update(entry.aggregations)

    expressions = [
        "avg_arr * 12",
        "avg_arr * (1 - avg_churn / 100)",
    ]
    variables = {**aggregations, "arr_growth": aggregations.get("avg_arr", 0.0) * 0.1}
    calc_agent = CalculatorAgent(variables=variables)
    results = calc_agent.evaluate(expressions)

    metrics: list[AnalyticsMetric] = []
    for calc_result in results:
        if calc_result.error:
            continue
        metrics.append(
            AnalyticsMetric(
                name=calc_result.expression,
                value=calc_result.value,
                unit="USD" if "arr" in calc_result.expression else "",
                trend="flat",
                period="annualized" if "* 12" in calc_result.expression else "current",
            )
        )

    finished = utc_now()
    timing = SubgraphTiming.from_times("analytics.calculator", started, finished)
    analytics = AnalyticsResult(
        kpis=metrics,
        aggregations=aggregations,
        calculations_performed=len(results),
    )
    return {
        "analytics_results": [analytics],
        "metadata": {
            "subgraph_timings": [timing.model_dump()],
            "state_transitions": [
                {"node": "analytics.calculator", "at": finished.isoformat()}
            ],
        },
    }


def _no_op_result(name: str, started: datetime, *, disabled: bool) -> dict[str, Any]:
    finished = utc_now()
    timing = SubgraphTiming.from_times(name, started, finished)
    analytics = AnalyticsResult(notes="disabled" if disabled else "no-op")
    return {
        "analytics_results": [analytics],
        "metadata": {
            "subgraph_timings": [timing.model_dump()],
            "state_transitions": [
                {"node": name, "at": finished.isoformat(), "skipped": disabled}
            ],
        },
    }


def build_analytics_graph(
    *,
    sql_agent: SQLAgent | None = None,
    calculator_agent: CalculatorAgent | None = None,
    config: AnalyticsConfig | None = None,
) -> Any:  # noqa: ANN401
    """Build the analytics subgraph."""
    if sql_agent is None:
        sql_agent = SQLAgent()
    if calculator_agent is None:
        calculator_agent = CalculatorAgent()
    if config is None:
        config = AnalyticsConfig()

    graph: StateGraph = StateGraph(GraphState)
    graph.add_node(
        "sql_agent",
        lambda state: _sql_node(state, agent=sql_agent, config=config),
    )
    graph.add_node(
        "calculator",
        lambda state: _calculator_node(state, agent=calculator_agent, config=config),
    )
    graph.add_edge(START, "sql_agent")
    graph.add_edge("sql_agent", "calculator")
    graph.add_edge("calculator", END)
    return graph.compile()


def run_analytics(
    state: GraphState,
    *,
    sql_agent: SQLAgent | None = None,
    calculator_agent: CalculatorAgent | None = None,
    config: AnalyticsConfig | None = None,
) -> dict[str, Any]:
    """Invoke the analytics subgraph against a state object."""
    graph = build_analytics_graph(
        sql_agent=sql_agent,
        calculator_agent=calculator_agent,
        config=config,
    )
    result: dict[str, Any] = graph.invoke(state)
    return result


__all__ = ["build_analytics_graph", "run_analytics"]
