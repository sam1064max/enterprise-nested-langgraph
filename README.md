# Enterprise Nested LangGraph

Production-grade, multi-agent research and analytics system built with
**LangGraph** and a hierarchical (nested) graph architecture.

[![Tests](https://img.shields.io/badge/tests-140%20passed-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)](tests/)
[![Ruff](https://img.shields.io/badge/ruff-clean-brightgreen)](pyproject.toml)
[![Mypy](https://img.shields.io/badge/mypy-clean-brightgreen)](pyproject.toml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

This project demonstrates how to compose **parent graphs**
(Supervisor) and **child subgraphs** (Research, Analytics, Reporting)
into a single, strongly-typed, observable, and testable AI system.

## Why This Project Exists

Building a serious LLM application is more than chaining prompts. It
requires:

* **Clear topology** — a supervisor that orchestrates specialized
  subgraphs.
* **Strict contracts** — Pydantic v2 schemas for every domain object.
* **Resilient state** — typed state with deterministic reducers.
* **Defense in depth** — input and output guardrails.
* **Operational hygiene** — structured logging, request/trace IDs,
  and LangSmith wiring.
* **Engineering rigor** — Ruff, Mypy, Pytest, Docker, CI, and 100%
  type hints.

This repository is the reference implementation.

## Architecture

```
User
  |
Input Guardrail
  |
Supervisor Graph
  |
  +-- Research Graph      (Planner -> Executor)
  +-- Analytics Graph     (SQL Agent -> Calculator)
  +-- Reporting Graph     (Writer -> Reviewer)
  |
Output Guardrail
  |
Final Response
```

| Component        | Responsibility                                                |
|------------------|---------------------------------------------------------------|
| Supervisor       | Orchestrates subgraphs, propagates shared state.              |
| Research Graph   | Decomposes the objective into tasks and gathers findings.     |
| Analytics Graph  | Runs SQL queries and AST-safe calculations.                   |
| Reporting Graph  | Composes the final report and validates quality.              |
| Input Guardrail  | Blocks prompt injection, jailbreaks, extraction, oversized.   |
| Output Guardrail | Redacts API keys, stack traces, internal markers.             |

## Highlights

- **Strongly-typed state** — Pydantic v2 + TypedDict with custom reducers.
- **Subgraph composition** — three independently testable subgraphs.
- **Guardrails** — input and output safety with 12 + 8 builtin patterns.
- **Observability** — `structlog` JSON logs, UUID request/trace IDs,
  LangSmith wiring, per-subgraph timings.
- **CI/CD** — Ruff, Mypy, Pytest, Docker, GitHub Actions.
- **111 tests** — all LLM calls are mocked; the suite runs in under 5
  seconds.

## Quick Start

```bash
# Install uv (https://github.com/astral-sh/uv)
# Then:
uv sync

cp .env.example .env
# Edit .env to set OPENAI_API_KEY (optional) and LANGCHAIN_TRACING_V2

uv run python app.py
```

## Project Layout

```
.
├── app.py                      # Top-level entrypoint
├── config/                     # YAML + Pydantic settings
├── models/                     # Schemas + GraphState
├── graphs/
│   ├── supervisor/             # Orchestrator
│   ├── research/               # Research subgraph
│   ├── analytics/              # Analytics subgraph
│   └── reporting/              # Reporting subgraph
├── tools/                      # In-memory search + AST calculator
├── guardrails/                 # Input + output safety
├── observability/              # structlog + LangSmith
├── tests/
│   ├── unit/                   # 72 unit tests
│   └── integration/            # 39 integration tests
├── docs/
│   ├── architecture.md
│   ├── setup.md
│   └── adr/                    # Architecture Decision Records
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Documentation

- [Architecture](docs/architecture.md)
- [Setup Guide](docs/setup.md)
- [ADR-001 — Subgraph Strategy](docs/adr/ADR-001-subgraph-strategy.md)
- [ADR-002 — State Management](docs/adr/ADR-002-state-management.md)
- [ADR-003 — Observability](docs/adr/ADR-003-observability.md)
- [ADR-004 — Error Handling](docs/adr/ADR-004-error-handling.md)

## Testing

```bash
uv run pytest                 # all tests
uv run pytest tests/unit      # unit only
uv run pytest tests/integration  # integration only
uv run ruff check .
uv run mypy .
```

## License

MIT
