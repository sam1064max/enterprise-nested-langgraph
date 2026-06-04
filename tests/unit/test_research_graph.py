"""Tests for the research subgraph."""

from __future__ import annotations

import pytest

from config.settings import ResearchConfig
from graphs.research.executor import execute_plan
from graphs.research.graph import build_research_graph, run_research
from graphs.research.planner import _split_into_segments, heuristic_planner
from models.schemas import ResearchTask
from models.state import create_initial_state
from tools.search import InMemorySearchClient


@pytest.fixture
def config() -> ResearchConfig:
    return ResearchConfig(max_steps=3, dedupe_results=True)


@pytest.fixture
def search_client() -> InMemorySearchClient:
    return InMemorySearchClient()


def test_split_into_segments_breaks_on_conjunctions() -> None:
    segments = _split_into_segments("Find trends, summarize findings, then list risks")
    assert "Find trends" in segments
    assert "summarize findings" in segments
    assert "list risks" in segments


def test_heuristic_planner_respects_max_steps(config: ResearchConfig) -> None:
    tasks = heuristic_planner(
        "Find trends and summarize findings then list risks and recommend actions",
        config,
    )
    assert 0 < len(tasks) <= config.max_steps
    assert all(isinstance(t, ResearchTask) for t in tasks)


def test_heuristic_planner_dedupes_when_enabled(config: ResearchConfig) -> None:
    config_no_dedupe = ResearchConfig(max_steps=10, dedupe_results=False)
    tasks = heuristic_planner("trends and trends and trends", config_no_dedupe)
    assert len(tasks) >= 1
    deduped = heuristic_planner("trends and trends and trends", config)
    assert len(deduped) <= len(tasks)


def test_heuristic_planner_fallback_for_empty() -> None:
    tasks = heuristic_planner("", ResearchConfig())
    assert tasks == []


def test_executor_returns_finding_per_task(
    search_client: InMemorySearchClient,
    config: ResearchConfig,
) -> None:
    tasks = [ResearchTask(objective="multi-agent architectures")]
    findings = execute_plan(tasks, search_client, config)
    assert len(findings) == 1
    assert findings[0].title


def test_executor_handles_zero_hits(
    search_client: InMemorySearchClient,
    config: ResearchConfig,
) -> None:
    tasks = [ResearchTask(objective="xyzqqq-novel-keyword-zzzz")]
    findings = execute_plan(tasks, search_client, config)
    assert findings[0].confidence == pytest.approx(0.1)
    assert "No evidence" in findings[0].title


def test_research_graph_runs_end_to_end(
    search_client: InMemorySearchClient,
    config: ResearchConfig,
) -> None:
    state = create_initial_state("Find trends and summarize findings")
    graph = build_research_graph(client=search_client, config=config)
    result = graph.invoke(state)
    assert result["research_plan"], "planner should populate the plan"
    assert result["research_results"], "executor should produce findings"
    timings = result["metadata"]["subgraph_timings"]
    assert any(t["name"] == "research.planner" for t in timings)
    assert any(t["name"] == "research.executor" for t in timings)


def test_run_research_helper(
    search_client: InMemorySearchClient,
    config: ResearchConfig,
) -> None:
    state = create_initial_state("Explore guardrails and observability")
    result = run_research(state, client=search_client, config=config)
    assert result["research_results"]
