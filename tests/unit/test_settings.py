"""Tests for the configuration management module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from config.settings import AppSettings, get_settings, reset_settings_cache

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None, None, None]:
    reset_settings_cache()
    yield
    reset_settings_cache()


def test_get_settings_returns_singleton() -> None:
    first = get_settings()
    second = get_settings()
    assert first is second


def test_default_settings_have_expected_values() -> None:
    settings = get_settings()
    assert settings.llm.provider == "openai"
    assert settings.llm.model == "gpt-4.1"
    assert settings.research.max_steps == 5
    assert settings.analytics.calculations_enabled is True
    assert settings.reporting.review_enabled is True
    assert settings.observability.langsmith_enabled is True
    assert settings.logging.level == "INFO"
    assert settings.app.name == "enterprise-nested-langgraph"


def test_invalid_temperature_raises() -> None:
    with pytest.raises(ValueError, match="temperature"):
        AppSettings(llm={"temperature": 5.0})  # type: ignore[arg-type]


def test_invalid_log_level_raises() -> None:
    with pytest.raises(ValueError, match="log level"):
        AppSettings(logging={"level": "VERBOSE"})  # type: ignore[arg-type]


def test_env_override_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_LOGGING__LEVEL", "DEBUG")
    reset_settings_cache()
    settings = get_settings()
    assert settings.logging.level == "DEBUG"


def test_init_kwarg_takes_precedence_over_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_LOGGING__LEVEL", "DEBUG")
    settings = AppSettings(logging={"level": "WARNING"})  # type: ignore[arg-type]
    assert settings.logging.level == "WARNING"
