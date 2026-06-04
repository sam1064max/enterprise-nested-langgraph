"""Reporting reviewer.

The reviewer validates a draft report produced by the writer. It
checks completeness (does the report cover all required sections?),
formatting (does every section have a heading and body?), and
consistency (does the report reference the request and trace IDs?).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from models.schemas import ReportReview, ReportSection

if TYPE_CHECKING:
    from config.settings import ReportingConfig
    from models.state import GraphState


_RECOMMENDED_HEADINGS: tuple[str, ...] = (
    "Executive Summary",
    "Findings",
    "Analytics",
    "Recommendations",
)
_STRICT_THRESHOLD = 0.7
_RELAXED_THRESHOLD = 0.5


def review_report(
    sections: list[ReportSection],
    state: GraphState,
    config: ReportingConfig,
    *,
    pass_number: int = 1,
) -> ReportReview:
    """Review a draft report.

    Args:
        sections: Sections produced by the writer.
        state: The current graph state (used for ID checks).
        config: Reporting configuration.
        pass_number: The current review pass number (1-indexed).

    Returns:
        A :class:`ReportReview` with scores, feedback, and a boolean
        approval flag. Approval is granted if all three scores are
        at least ``_STRICT_THRESHOLD`` and the report has at least
        the recommended sections.
    """
    if not config.review_enabled:
        return ReportReview(
            approved=True,
            completeness_score=1.0,
            formatting_score=1.0,
            consistency_score=1.0,
            feedback="review disabled by configuration",
            pass_number=pass_number,
        )

    completeness = _score_completeness(sections)
    formatting = _score_formatting(sections)
    consistency = _score_consistency(sections, state)
    feedback = _build_feedback(completeness, formatting, consistency)

    approved = (
        completeness >= _STRICT_THRESHOLD
        and formatting >= _STRICT_THRESHOLD
        and consistency >= _STRICT_THRESHOLD
        and len(sections) >= len(_RECOMMENDED_HEADINGS)
    )
    if pass_number >= config.max_review_passes and not approved:
        approved = (
            completeness >= _RELAXED_THRESHOLD
            and formatting >= _RELAXED_THRESHOLD
            and consistency >= _RELAXED_THRESHOLD
        )
        feedback = f"{feedback} (final pass: accepted with reservations)"

    return ReportReview(
        approved=approved,
        completeness_score=completeness,
        formatting_score=formatting,
        consistency_score=consistency,
        feedback=feedback,
        pass_number=pass_number,
    )


def _score_completeness(sections: list[ReportSection]) -> float:
    headings = {section.heading.strip().lower() for section in sections}
    if not headings:
        return 0.0
    required = {h.lower() for h in _RECOMMENDED_HEADINGS}
    return len(headings & required) / len(required)


def _score_formatting(sections: list[ReportSection]) -> float:
    if not sections:
        return 0.0
    ok = sum(1 for s in sections if s.heading.strip() and s.body.strip())
    return ok / len(sections)


def _score_consistency(sections: list[ReportSection], state: GraphState) -> float:
    body = "\n".join(s.body for s in sections)
    score = 0.0
    if state.get("request_id") and state["request_id"] in body:
        score += 0.5
    if state.get("trace_id") and state["trace_id"] in body:
        score += 0.5
    return score


def _build_feedback(completeness: float, formatting: float, consistency: float) -> str:
    parts: list[str] = []
    if completeness < _STRICT_THRESHOLD:
        parts.append("Add missing recommended sections.")
    if formatting < _STRICT_THRESHOLD:
        parts.append("Some sections have empty headings or bodies.")
    if consistency < _STRICT_THRESHOLD:
        parts.append("Include request_id and trace_id in the report.")
    if not parts:
        parts.append("Report looks good.")
    return " ".join(parts)


__all__ = ["review_report"]
