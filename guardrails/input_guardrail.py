"""Input guardrail.

The input guardrail validates user-submitted queries before they are
sent to the supervisor graph. It rejects:

* queries exceeding the configured maximum length;
* queries that match configured ``block_patterns`` (regex);
* queries that match any built-in jailbreak / prompt-extraction
  signature (defense in depth).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from models.schemas import GuardrailViolation, Severity

if TYPE_CHECKING:
    from config.settings import GuardrailsConfig, InputGuardrailConfig


__all__ = ["GuardrailResult", "InputGuardrail"]


_BUILTIN_SIGNATURES: tuple[str, ...] = (
    r"ignore\s+(?:all|previous|prior|the)\s+instructions?",
    r"disregard\s+(?:all|previous|prior|the)\s+(?:rules|instructions?)",
    r"forget\s+(?:all|everything|your)\s+(?:rules|instructions?)",
    r"reveal\s+(?:\w+\s+)*(?:system|hidden)\s+prompt",
    r"show\s+(?:\w+\s+)*(?:system|hidden)\s+(?:prompt|instructions?)",
    r"what\s+is\s+your\s+(?:system|hidden)\s+prompt",
    r"act\s+as\s+(?:an?\s+)?(?:unrestricted|jailbroken|developer)(?:\s+\w+){0,4}\s+mode",
    r"print\s+(?:the\s+)?system\s+prompt",
    r"repeat\s+(?:the\s+)?words?\s+above",
    r"system\s*:\s*you\s+are",
    r"<\|im_start\|>",
    r"```system",
)

_BUILTIN_SEVERITY = Severity.CRITICAL


@dataclass(frozen=True)
class GuardrailResult:
    """Result of a guardrail check."""

    passed: bool
    reason: str = ""
    violations: tuple[GuardrailViolation, ...] = ()


class InputGuardrail:
    """Validate incoming user queries against configured patterns."""

    def __init__(self, config: GuardrailsConfig) -> None:
        self._config: InputGuardrailConfig = config.input
        self._patterns: tuple[re.Pattern[str], ...] = self._compile(
            self._config.block_patterns
        )
        self._builtin: tuple[re.Pattern[str], ...] = tuple(
            re.compile(p, re.IGNORECASE) for p in _BUILTIN_SIGNATURES
        )

    @staticmethod
    def _compile(patterns: list[str]) -> tuple[re.Pattern[str], ...]:
        compiled: list[re.Pattern[str]] = []
        for pattern in patterns:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                # Skip invalid patterns to keep the system available.
                continue
        return tuple(compiled)

    def check(self, query: str) -> GuardrailResult:
        """Check ``query`` against the configured guardrails.

        Args:
            query: The user-submitted query string.

        Returns:
            A :class:`GuardrailResult` indicating whether the query is
            allowed. If rejected, the ``violations`` tuple contains
            the matched patterns and severities.
        """
        if not self._config.enabled:
            return GuardrailResult(passed=True)

        violations: list[GuardrailViolation] = []

        if len(query) > self._config.max_query_length:
            violations.append(
                GuardrailViolation(
                    category="length",
                    pattern=f"length>{self._config.max_query_length}",
                    severity=Severity.MEDIUM,
                    description=f"Query length {len(query)} exceeds limit.",
                )
            )

        for pattern in self._builtin:
            match = pattern.search(query)
            if match:
                violations.append(
                    GuardrailViolation(
                        category="prompt_injection",
                        pattern=match.group(0),
                        severity=_BUILTIN_SEVERITY,
                        description="Matched a built-in prompt-injection signature.",
                    )
                )

        for pattern in self._patterns:
            match = pattern.search(query)
            if match:
                violations.append(
                    GuardrailViolation(
                        category="configured_block",
                        pattern=match.group(0),
                        severity=Severity.HIGH,
                        description="Matched a configured block pattern.",
                    )
                )

        if violations:
            reason = "; ".join(f"{v.category}:{v.pattern}" for v in violations)
            return GuardrailResult(passed=False, reason=reason, violations=tuple(violations))

        return GuardrailResult(passed=True)


__all__ = ["GuardrailResult", "InputGuardrail"]
