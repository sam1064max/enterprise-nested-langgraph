"""Configuration management using Pydantic Settings.

This module loads configuration from three sources, in order of precedence
(highest first):

1. Arguments passed to ``AppSettings(...)``.
2. Environment variables prefixed with ``APP_``.
3. ``.env`` file (loaded by Pydantic Settings).
4. ``config/config.yaml`` (defaults).

All configuration is strongly typed via Pydantic v2 and validated at
startup. The application must call :func:`get_settings` exactly once
per process; the returned object is cached.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

CONFIG_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CONFIG_DIR.parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yaml"
_MAX_TEMPERATURE = 2.0


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = "openai"
    model: str = "gpt-4.1"
    temperature: float = 0.2
    max_tokens: int = 2000
    request_timeout_seconds: int = 60
    max_retries: int = 3

    @field_validator("temperature")
    @classmethod
    def _validate_temperature(cls, value: float) -> float:
        if not 0.0 <= value <= _MAX_TEMPERATURE:
            raise ValueError(f"temperature must be between 0.0 and {_MAX_TEMPERATURE}")
        return value


class ResearchConfig(BaseModel):
    """Research subgraph configuration."""

    max_steps: int = 5
    dedupe_results: bool = True
    planner_instructions: str = ""


class AnalyticsConfig(BaseModel):
    """Analytics subgraph configuration."""

    calculations_enabled: bool = True
    sql_enabled: bool = True
    safe_eval: bool = True
    default_currency: str = "USD"


class ReportingConfig(BaseModel):
    """Reporting subgraph configuration."""

    review_enabled: bool = True
    max_review_passes: int = 2
    writer_instructions: str = ""


class InputGuardrailConfig(BaseModel):
    """Input guardrail configuration."""

    enabled: bool = True
    max_query_length: int = 4000
    block_patterns: list[str] = Field(default_factory=list)


class OutputGuardrailConfig(BaseModel):
    """Output guardrail configuration."""

    enabled: bool = True
    redact_patterns: list[str] = Field(default_factory=list)


class GuardrailsConfig(BaseModel):
    """Guardrails container."""

    input: InputGuardrailConfig = Field(default_factory=InputGuardrailConfig)
    output: OutputGuardrailConfig = Field(default_factory=OutputGuardrailConfig)


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    langsmith_enabled: bool = True
    langchain_tracing_v2: bool = True
    log_state_transitions: bool = True


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"
    include_timestamp: bool = True
    include_request_id: bool = True

    @field_validator("level")
    @classmethod
    def _validate_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"log level must be one of {sorted(allowed)}")
        return upper


class AppConfig(BaseModel):
    """Application-level configuration."""

    name: str = "enterprise-nested-langgraph"
    version: str = "0.1.0"
    environment: str = "development"


class _YamlSettingsSource(PydanticBaseSettingsSource):
    """Custom settings source that reads ``config/config.yaml`` as defaults."""

    yaml_path: ClassVar[Path] = DEFAULT_CONFIG_PATH

    def get_field_value(
        self,
        _field: Any,  # noqa: ANN401
        field_name: str,
    ) -> tuple[Any, str, bool]:
        yaml_data = self._load_yaml()
        field_value = yaml_data.get(field_name)
        return field_value, field_name, False

    def prepare_field_value(
        self,
        _field_name: str,
        _field: Any,  # noqa: ANN401
        value: Any,  # noqa: ANN401
        _value_is_complex: bool,
    ) -> Any:  # noqa: ANN401
        return value

    def __call__(self) -> dict[str, Any]:
        return self._load_yaml()

    @staticmethod
    def _load_yaml() -> dict[str, Any]:
        if not _YamlSettingsSource.yaml_path.exists():
            return {}
        with _YamlSettingsSource.yaml_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError("Invalid YAML config: must be a mapping at the root")
        return data


class AppSettings(BaseSettings):
    """Root application settings.

    The default values for fields are populated from ``config/config.yaml``
    via :class:`_YamlSettingsSource`. Environment variables prefixed with
    ``APP_`` override these defaults, and explicit constructor arguments
    take the highest precedence.
    """

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    llm: LLMConfig = Field(default_factory=LLMConfig)
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    analytics: AnalyticsConfig = Field(default_factory=AnalyticsConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    app: AppConfig = Field(default_factory=AppConfig)

    openai_api_key: str | None = None
    langsmith_api_key: str | None = None
    langchain_api_key: str | None = None
    langchain_project: str | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Return the source chain: init > env > dotenv > yaml > secrets."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            _YamlSettingsSource(settings_cls),
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return the cached application settings.

    The settings object is built once per process. Subsequent calls
    return the cached instance, ensuring configuration is not mutated
    at runtime.
    """
    try:
        return AppSettings()
    except Exception as exc:
        raise SystemExit(f"Failed to load configuration: {exc}") from exc


def reset_settings_cache() -> None:
    """Clear the cached settings (used by tests)."""
    get_settings.cache_clear()


def reload_settings_from_path(path: Path) -> None:
    """Override the YAML path used by :class:`_YamlSettingsSource` (tests)."""
    _YamlSettingsSource.yaml_path = path
    reset_settings_cache()


__all__ = [  # noqa: RUF022
    "AnalyticsConfig",
    "AppConfig",
    "AppSettings",
    "DEFAULT_CONFIG_PATH",
    "GuardrailsConfig",
    "InputGuardrailConfig",
    "LLMConfig",
    "LoggingConfig",
    "ObservabilityConfig",
    "OutputGuardrailConfig",
    "PROJECT_ROOT",
    "ReportingConfig",
    "ResearchConfig",
    "get_settings",
    "reload_settings_from_path",
    "reset_settings_cache",
]


if __name__ == "__main__":  # pragma: no cover
    settings = get_settings()
    print(f"Loaded configuration for {settings.app.name} v{settings.app.version}")
    print(f"LLM model: {settings.llm.model}")
    print(f"Log level: {settings.logging.level}")
