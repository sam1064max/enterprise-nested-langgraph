"""Search tool used by the research executor.

This module defines a simple, dependency-injectable search interface
so that production code can plug in a real search client (Tavily,
Bing, Google CSE, etc.) while tests can plug in a deterministic mock.

The default implementation is :class:`InMemorySearchClient` which
returns canned results. The real LLM-driven graph should construct an
``InMemorySearchClient`` (or a custom subclass) and pass it into the
research executor at wiring time.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

_MIN_TOKEN_LENGTH = 2
_MAX_RESULTS = 5


@dataclass(frozen=True)
class SearchHit:
    """A single search result."""

    title: str
    url: str
    snippet: str
    score: float = 0.5


@dataclass
class SearchResponse:
    """The result of a single search query."""

    query: str
    hits: list[SearchHit] = field(default_factory=list)


class SearchClient(ABC):
    """Abstract base class for search clients."""

    @abstractmethod
    def search(self, query: str, *, max_results: int = _MAX_RESULTS) -> SearchResponse:
        """Execute ``query`` and return up to ``max_results`` hits."""


_CORPUS: tuple[dict[str, str], ...] = (
    {
        "title": "Enterprise AI Adoption Report 2026",
        "url": "https://example.com/enterprise-ai-2026",
        "snippet": (
            "Large enterprises continue to invest in generative AI, "
            "with 78% of Fortune 500 companies reporting at least "
            "one production AI system in 2026."
        ),
        "keywords": "enterprise,ai,adoption,generative,production,investment",
    },
    {
        "title": "Multi-Agent Architectures in Practice",
        "url": "https://example.com/multi-agent-architectures",
        "snippet": (
            "Hierarchical multi-agent systems separate planning from "
            "execution and use shared state to coordinate subgraphs."
        ),
        "keywords": "multi-agent,hierarchical,planner,executor,state,subgraph",
    },
    {
        "title": "LangGraph: Composable Agent Graphs",
        "url": "https://example.com/langgraph-composition",
        "snippet": (
            "LangGraph enables strongly-typed state machines with "
            "reducers, subgraphs, and human-in-the-loop checkpoints."
        ),
        "keywords": "langgraph,state,subgraph,reducer,checkpoint",
    },
    {
        "title": "Observability for LLM Applications",
        "url": "https://example.com/llm-observability",
        "snippet": (
            "Tracing, structured logging, and request IDs are "
            "essential for operating LLM systems in production."
        ),
        "keywords": "observability,tracing,logging,llm,production",
    },
    {
        "title": "Guardrails and Prompt-Injection Defenses",
        "url": "https://example.com/prompt-injection",
        "snippet": (
            "Input and output guardrails mitigate prompt injection, "
            "jailbreaks, and accidental secret leakage."
        ),
        "keywords": "guardrail,prompt,injection,jailbreak,security,redaction",
    },
    {
        "title": "Financial KPIs for SaaS Companies",
        "url": "https://example.com/saas-kpis",
        "snippet": (
            "ARR, NRR, gross margin, and CAC payback are the core "
            "financial KPIs for subscription software businesses."
        ),
        "keywords": "kpi,arr,nrr,margin,cac,saas,finance,metric",
    },
)


class InMemorySearchClient(SearchClient):
    """A deterministic, in-memory search client for tests and demos.

    The client matches queries by keyword against a small static corpus
    and ranks hits by the number of keyword matches. This makes the
    research subgraph fully testable without any external service.
    """

    def search(self, query: str, *, max_results: int = _MAX_RESULTS) -> SearchResponse:
        tokens = {t.lower() for t in re.findall(r"\w+", query) if len(t) > _MIN_TOKEN_LENGTH}
        if not tokens:
            return SearchResponse(query=query, hits=[])

        scored: list[tuple[int, SearchHit]] = []
        for entry in _CORPUS:
            keyword_set = set(entry["keywords"].split(","))
            overlap = len(tokens & keyword_set)
            if overlap == 0:
                continue
            hit = SearchHit(
                title=entry["title"],
                url=entry["url"],
                snippet=entry["snippet"],
                score=overlap / len(tokens | keyword_set),
            )
            scored.append((overlap, hit))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = [hit for _, hit in scored[:max_results]]
        return SearchResponse(query=query, hits=top)


__all__ = [
    "InMemorySearchClient",
    "SearchClient",
    "SearchHit",
    "SearchResponse",
]
