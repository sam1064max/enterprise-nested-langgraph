"""Pytest configuration and shared fixtures."""

from __future__ import annotations

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


@pytest.fixture(autouse=True)
def _reset_settings_cache_fixture() -> Generator[None, None, None]:
    reset_settings_cache()
    yield
    reset_settings_cache()
