"""Tracing primitives for the Enterprise Nested LangGraph system.

The module exposes :func:`generate_request_id` and
:func:`generate_trace_id` so the rest of the codebase can produce
strongly-typed identifiers without depending on a specific
distributed-tracing library. LangSmith integration is also handled
here: when ``LANGSMITH_API_KEY`` is set, this module exports the
environment variables required by LangChain to enable tracing.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def generate_request_id() -> str:
    """Return a new request ID."""
    return f"req_{uuid.uuid4().hex}"


def generate_trace_id() -> str:
    """Return a new trace ID."""
    return f"trc_{uuid.uuid4().hex}"


def configure_langsmith(settings: Any) -> None:  # noqa: ANN401
    """Configure LangSmith environment variables.

    Reads ``LANGSMITH_API_KEY`` from environment and sets the
    ``LANGCHAIN_*`` variables expected by LangChain. If
    ``observability.langsmith_enabled`` is False the function is a
    no-op.
    """
    if not getattr(settings.observability, "langsmith_enabled", False):
        logger.info("langsmith_disabled")
        return

    api_key = os.environ.get("LANGSMITH_API_KEY") or settings.langsmith_api_key
    if not api_key:
        logger.warning("langsmith_no_api_key")
        return

    os.environ["LANGCHAIN_TRACING_V2"] = (
        "true" if settings.observability.langchain_tracing_v2 else "false"
    )
    os.environ["LANGCHAIN_API_KEY"] = api_key
    project = os.environ.get("LANGCHAIN_PROJECT") or settings.langchain_project
    if project:
        os.environ["LANGCHAIN_PROJECT"] = project
    os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
    logger.info("langsmith_configured", extra={"project": project or "default"})


def with_trace_context(bound_logger: Any, **kwargs: Any) -> Any:  # noqa: ANN401
    """Bind trace context variables to ``bound_logger``."""
    return bound_logger.bind(**kwargs)


__all__ = [
    "configure_langsmith",
    "generate_request_id",
    "generate_trace_id",
    "with_trace_context",
]
