"""Top-level entrypoint for the Enterprise Nested LangGraph application.

The application wires together configuration, observability, guardrails,
and the supervisor graph so that the system can be invoked with a single
user query and return a final report.
"""

from __future__ import annotations

import sys
from typing import Any, cast

from config.settings import get_settings
from graphs.supervisor.graph import build_supervisor_graph
from guardrails.input_guardrail import InputGuardrail
from guardrails.output_guardrail import OutputGuardrail
from models.state import GraphState, create_initial_state
from observability.logging import configure_logging, get_logger
from observability.tracing import generate_request_id, generate_trace_id

logger = get_logger(__name__)


def run(query: str) -> dict[str, Any]:
    """Run the full pipeline for a single user query.

    Args:
        query: The natural-language objective submitted by the user.

    Returns:
        The final graph state containing the report and metadata.
    """
    settings = get_settings()
    configure_logging(settings.logging)

    request_id = generate_request_id()
    trace_id = generate_trace_id()
    logger.info(
        "pipeline_start",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "query_length": len(query),
        },
    )

    input_guard = InputGuardrail(settings.guardrails)
    guard_result = input_guard.check(query)
    if not guard_result.passed:
        logger.warning("input_guardrail_rejected", extra={"reason": guard_result.reason})
        return _reject(request_id, trace_id, guard_result.reason)

    initial_state: GraphState = create_initial_state(
        query=query,
        request_id=request_id,
        trace_id=trace_id,
    )

    supervisor = build_supervisor_graph()
    final_state_any: Any = supervisor.invoke(initial_state)
    final_state = cast("dict[str, Any]", final_state_any)

    output_guard = OutputGuardrail(settings.guardrails)
    report = final_state.get("report", "")
    redacted = output_guard.redact(report)

    if redacted.redactions:
        logger.info(
            "output_guardrail_redactions",
            extra={"count": len(redacted.redactions), "request_id": request_id},
        )
        final_state["report"] = redacted.text
        final_state["metadata"]["output_redactions"] = [r.category for r in redacted.redactions]

    logger.info("pipeline_end", extra={"request_id": request_id, "trace_id": trace_id})
    return final_state


def _reject(request_id: str, trace_id: str, reason: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": "",
        "research_results": [],
        "analytics_results": [],
        "report": f"Request rejected by input guardrail: {reason}",
        "metadata": {"rejected": True, "reason": reason},
        "error": reason,
        "trace_id": trace_id,
        "request_id": request_id,
        "execution_time": 0.0,
    }
    return payload


def main() -> int:
    query = " ".join(sys.argv[1:]) or "Summarize the latest enterprise AI trends."
    result = run(query)
    print(result.get("report", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
