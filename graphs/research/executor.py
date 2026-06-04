"""Research executor.

The executor consumes a list of :class:`ResearchTask` instances and
produces :class:`ResearchFinding` objects by querying an injected
search client. The function is pure (no global state, no I/O) so it
can be unit-tested in isolation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from models.schemas import ResearchFinding, ResearchTask

if TYPE_CHECKING:
    from collections.abc import Iterable

    from config.settings import ResearchConfig
    from tools.search import SearchClient, SearchHit


def execute_plan(
    tasks: Iterable[ResearchTask],
    client: SearchClient,
    config: ResearchConfig,
) -> list[ResearchFinding]:
    """Execute each task against the search client.

    Args:
        tasks: Tasks to execute. Tasks are executed in input order.
        client: Search client used to gather evidence.
        config: Research configuration (used for max_steps enforcement).

    Returns:
        One :class:`ResearchFinding` per task. Tasks that produce no
        search hits yield a low-confidence finding with an explicit
        "no evidence" summary.
    """
    findings: list[ResearchFinding] = []
    for index, task in enumerate(tasks, start=1):
        if index > config.max_steps:
            break
        response = client.search(task.objective, max_results=3)
        if not response.hits:
            findings.append(
                ResearchFinding(
                    task_id=task.id,
                    title=f"No evidence: {task.objective}",
                    summary="No search results matched this task.",
                    source="none",
                    confidence=0.1,
                )
            )
            continue

        top = response.hits[0]
        summary = "; ".join(h.snippet for h in response.hits)
        findings.append(
            ResearchFinding(
                task_id=task.id,
                title=top.title,
                summary=summary,
                source=top.url,
                confidence=_confidence_from_hits(response.hits),
            )
        )

    return findings


def _confidence_from_hits(hits: list[SearchHit]) -> float:
    """Return a confidence score in [0, 1] based on hit scores."""
    if not hits:
        return 0.0
    return max(0.0, min(1.0, sum(h.score for h in hits) / len(hits)))


__all__ = ["execute_plan"]
