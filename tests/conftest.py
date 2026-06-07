"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from config.settings import reset_settings_cache

if TYPE_CHECKING:
    from collections.abc import Generator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Disable LangSmith tracing for the entire test session — we don't have
# a real API key in CI and the supervisor graph will try to POST traces
# otherwise.
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGCHAIN_API_KEY", "")
os.environ.setdefault("LANGSMITH_API_KEY", "")
os.environ.setdefault("LANGSMITH_TRACING", "false")


@pytest.fixture(autouse=True)
def _reset_settings_cache_fixture() -> Generator[None, None, None]:
    reset_settings_cache()
    yield
    reset_settings_cache()
