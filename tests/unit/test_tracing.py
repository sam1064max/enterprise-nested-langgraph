"""Tests for the tracing module."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import structlog

from observability.tracing import (
    configure_langsmith,
    generate_request_id,
    generate_trace_id,
    with_trace_context,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch  # noqa: PT013


def test_generate_request_id_has_prefix() -> None:
    rid = generate_request_id()
    assert rid.startswith("req_")
    assert len(rid) > len("req_")


def test_generate_trace_id_has_prefix() -> None:
    tid = generate_trace_id()
    assert tid.startswith("trc_")
    assert len(tid) > len("trc_")


def test_request_and_trace_ids_are_unique() -> None:
    request_ids = {generate_request_id() for _ in range(50)}
    trace_ids = {generate_trace_id() for _ in range(50)}
    assert len(request_ids) == 50
    assert len(trace_ids) == 50
    assert request_ids.isdisjoint(trace_ids)


def test_configure_langsmith_disabled_is_noop() -> None:
    settings = MagicMock()
    settings.observability.langsmith_enabled = False
    configure_langsmith(settings)
    assert os.environ.get("LANGCHAIN_TRACING_V2") != "true"


def test_configure_langsmith_no_api_key_warns(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    settings = MagicMock()
    settings.observability.langsmith_enabled = True
    settings.observability.langchain_tracing_v2 = True
    settings.langsmith_api_key = None
    configure_langsmith(settings)
    assert os.environ.get("LANGCHAIN_TRACING_V2") != "true"


def test_configure_langsmith_with_api_key_enables_tracing() -> None:
    settings = MagicMock()
    settings.observability.langsmith_enabled = True
    settings.observability.langchain_tracing_v2 = True
    settings.langsmith_api_key = "lsv2_test_key_1234567890"
    settings.langchain_project = "enterprise-nested-langgraph"
    configure_langsmith(settings)
    assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
    assert os.environ.get("LANGCHAIN_API_KEY") == "lsv2_test_key_1234567890"
    assert os.environ.get("LANGCHAIN_PROJECT") == "enterprise-nested-langgraph"
    assert os.environ.get("LANGCHAIN_ENDPOINT") == "https://api.smith.langchain.com"


def test_configure_langsmith_respects_existing_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LANGCHAIN_PROJECT", "preexisting-project")
    settings = MagicMock()
    settings.observability.langsmith_enabled = True
    settings.observability.langchain_tracing_v2 = False
    settings.langsmith_api_key = "lsv2_existing_key"
    settings.langchain_project = "should-not-override"
    configure_langsmith(settings)
    assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"
    assert os.environ.get("LANGCHAIN_PROJECT") == "preexisting-project"


def test_configure_langsmith_env_var_fallback(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_from_env")
    settings = MagicMock()
    settings.observability.langsmith_enabled = True
    settings.observability.langchain_tracing_v2 = True
    settings.langsmith_api_key = None
    settings.langchain_project = "fallback-test"
    configure_langsmith(settings)
    assert os.environ.get("LANGCHAIN_API_KEY") == "lsv2_from_env"


def test_with_trace_context_binds_attributes() -> None:
    logger = structlog.get_logger("trace-test")
    bound = with_trace_context(logger, request_id="req_1", trace_id="trc_1")
    assert bound is not None
    assert callable(bound.info)
    assert callable(bound.error)


def test_generate_id_helper_returns_string() -> None:
    rid = generate_request_id()
    assert isinstance(rid, str)
    assert "_" in rid
