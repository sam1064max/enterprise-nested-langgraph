"""Research planner.

The planner decomposes a user objective into a small number of atomic
research tasks. The default implementation is deterministic and rule-
based so the system can run end-to-end without an LLM. Production
deployments can inject a planner that calls an LLM via dependency
injection.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from config.settings import ResearchConfig
from models.schemas import ResearchTask

PlannerFn = Callable[[str, ResearchConfig], list[ResearchTask]]


def heuristic_planner(query: str, config: ResearchConfig) -> list[ResearchTask]:
    """Generate research tasks using simple heuristics.

    The heuristic planner splits the objective on conjunctions and
    punctuation, generates one task per segment, and caps the count
    at ``config.max_steps``. It is deterministic and dependency-free.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    segments = _split_into_segments(cleaned)
    tasks: list[ResearchTask] = []
    seen_objectives: set[str] = set()

    for index, segment in enumerate(segments, start=1):
        objective = segment.strip().rstrip(".").strip()
        if not objective:
            continue
        key = objective.lower()
        if not config.dedupe_results or key not in seen_objectives:
            seen_objectives.add(key)
            tasks.append(
                ResearchTask(
                    objective=objective,
                    rationale=f"Derived from segment {index} of the user objective.",
                    priority=1,
                    dependencies=[],
                )
            )
        if len(tasks) >= config.max_steps:
            break

    if not tasks:
        tasks.append(
            ResearchTask(
                objective=cleaned,
                rationale="Fallback: no segments could be derived; using the full objective.",
            )
        )

    return tasks


def _split_into_segments(text: str) -> list[str]:
    """Split a text into research segments."""
    text = re.sub(r"\s+", " ", text)
    pattern = r"(?:,|;|\.| and | then | also | plus |, and )"
    parts = re.split(pattern, text, flags=re.IGNORECASE)
    return [p.strip(" ,;.") for p in parts if p.strip(" ,;.")]


__all__ = ["PlannerFn", "heuristic_planner"]
