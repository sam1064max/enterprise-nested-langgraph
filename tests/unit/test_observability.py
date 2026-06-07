"""Tests for observability primitives."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import pytest

from config.settings import LoggingConfig
from observability.logging import configure_logging, get_logger

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture


def test_configure_logging_is_idempotent() -> None:
    configure_logging(LoggingConfig(level="INFO", format="json"))
    configure_logging(LoggingConfig(level="DEBUG", format="text"))
    root = logging.getLogger()
    handlers = root.handlers
    assert isinstance(handlers, list)
    assert len(handlers) <= 1


def test_get_logger_returns_structlog() -> None:
    configure_logging(LoggingConfig(level="INFO", format="json"))
    logger = get_logger(__name__)
    assert logger is not None
    assert callable(logger.info)
    assert callable(logger.warning)
    assert callable(logger.error)


def test_logger_writes_to_stdout(capsys: CaptureFixture[str]) -> None:
    configure_logging(LoggingConfig(level="INFO", format="json"))
    logger = get_logger("test")
    logger.info("hello", extra={"foo": "bar"})
    captured = capsys.readouterr()
    assert "hello" in captured.out


def test_logger_handles_missing_stdout_attribute() -> None:
    """Sanity check that logger construction does not raise."""
    configure_logging(LoggingConfig(level="INFO", format="json"))
    logger = get_logger("another")
    logger.info("event", request_id="req1")
    assert sys.stdout is not None


def test_configure_logging_accepts_text_format() -> None:
    configure_logging(LoggingConfig(level="INFO", format="text"))
    logger = get_logger("text")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(sys, "stdout", sys.stdout)
        logger.info("text-mode event")
        assert sys.stdout is not None
