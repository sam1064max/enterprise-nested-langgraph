"""Structured logging for the Enterprise Nested LangGraph system.

This module configures :mod:`structlog` to emit JSON-formatted log
records. The application must call :func:`configure_logging` exactly
once at startup. Subsequent calls are no-ops so tests can call it
freely without duplicating handlers.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from config.settings import LoggingConfig


class _LoggingState:
    """Encapsulates the module-level ``configured`` flag.

    Using a class attribute avoids ``global`` statements which
    :mod:`ruff` flags as discouraged.
    """

    configured: bool = False


def configure_logging(config: LoggingConfig) -> None:
    """Configure :mod:`structlog` and stdlib logging.

    Args:
        config: Logging configuration object.
    """
    if _LoggingState.configured:
        return

    level = getattr(logging, config.level.upper(), logging.INFO)
    timestamper = structlog.processors.TimeStamper(fmt="iso") if config.include_timestamp else None

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _add_app_metadata,
    ]
    if timestamper is not None:
        shared_processors.append(timestamper)

    if config.format == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)
    _LoggingState.configured = True


def _add_app_metadata(
    _logger: Any,  # noqa: ANN401
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Inject a static ``app`` key into every log record."""
    event_dict.setdefault("app", "enterprise-nested-langgraph")
    return event_dict


def get_logger(name: str) -> Any:  # noqa: ANN401
    """Return a :mod:`structlog` logger bound to ``name``."""
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]
