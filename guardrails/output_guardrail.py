"""Output guardrail.

The output guardrail scrubs sensitive material from the final report
and any LLM-generated text that flows through the system. It detects
and redacts:

* API keys (e.g. ``sk-...``);
* common secret / token markers;
* stack traces and internal error markers;
* generic ``KEY=VALUE`` style secrets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from models.schemas import GuardrailViolation, Severity

if TYPE_CHECKING:
    from config.settings import GuardrailsConfig, OutputGuardrailConfig

_BUILTIN_REDACTORS: tuple[tuple[str, re.Pattern[str], Severity], ...] = (
    (
        "openai_api_key",
        re.compile(r"sk-[A-Za-z0-9]{16,}"),
        Severity.CRITICAL,
    ),
    (
        "aws_access_key",
        re.compile(r"AKIA[0-9A-Z]{16}"),
        Severity.CRITICAL,
    ),
    (
        "github_pat",
        re.compile(r"ghp_[A-Za-z0-9]{30,}"),
        Severity.CRITICAL,
    ),
    (
        "google_api_key",
        re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
        Severity.CRITICAL,
    ),
    (
        "env_assignment",
        re.compile(r"(?i)(?:openai_api_key|api[_-]?key|secret|password|token)\s*=\s*[^\s]+"),
        Severity.HIGH,
    ),
    (
        "bearer_token",
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
        Severity.HIGH,
    ),
    (
        "stack_trace",
        re.compile(r"Traceback \(most recent call last\):"),
        Severity.MEDIUM,
    ),
    (
        "internal_marker",
        re.compile(r"<\|/?im_start\|>|<\|/?im_end\|>"),
        Severity.MEDIUM,
    ),
    (
        "system_prompt_leak",
        re.compile(r"(?i)(?:my|the)\s+system\s+prompt\s+is"),
        Severity.MEDIUM,
    ),
)


_REDACTION = "[REDACTED]"


@dataclass
class Redaction:
    """A single redaction event."""

    category: str
    pattern: str
    severity: Severity
    original: str


@dataclass
class RedactionResult:
    """Outcome of running the output guardrail on a string."""

    text: str
    redactions: list[Redaction] = field(default_factory=list)

    @property
    def has_redactions(self) -> bool:
        return bool(self.redactions)


class OutputGuardrail:
    """Redact sensitive material from LLM outputs and final reports."""

    def __init__(self, config: GuardrailsConfig) -> None:
        self._config: OutputGuardrailConfig = config.output
        self._redactors: list[tuple[str, re.Pattern[str], Severity]] = list(_BUILTIN_REDACTORS)
        for pattern in self._config.redact_patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
            except re.error:
                continue
            self._redactors.append(("configured", compiled, Severity.HIGH))

    def redact(self, text: str) -> RedactionResult:
        """Apply all configured redactors to ``text``.

        Args:
            text: The text to scrub.

        Returns:
            A :class:`RedactionResult` with the scrubbed text and a
            list of :class:`Redaction` events for audit logging.
        """
        if not self._config.enabled:
            return RedactionResult(text=text)

        redactions: list[Redaction] = []
        scrubbed = text
        for category, pattern, severity in self._redactors:
            matches = list(pattern.finditer(scrubbed))
            if not matches:
                continue
            for match in reversed(matches):
                original = match.group(0)
                redactions.append(
                    Redaction(
                        category=category,
                        pattern=pattern.pattern,
                        severity=severity,
                        original=original,
                    )
                )
                scrubbed = (
                    scrubbed[: match.start()] + _REDACTION + scrubbed[match.end() :]
                )

        return RedactionResult(text=scrubbed, redactions=redactions)

    def violations(self, result: RedactionResult) -> list[GuardrailViolation]:
        """Convert redactions into Pydantic :class:`GuardrailViolation`."""
        return [
            GuardrailViolation(
                category=r.category,
                pattern=r.pattern,
                severity=r.severity,
                description="Sensitive material redacted from output.",
            )
            for r in result.redactions
        ]


__all__ = ["OutputGuardrail", "Redaction", "RedactionResult"]
