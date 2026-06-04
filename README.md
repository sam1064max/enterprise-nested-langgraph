# Enterprise Nested LangGraph

Production-grade, multi-agent research and analytics system built with **LangGraph** and a hierarchical (nested) graph architecture.

This project demonstrates how to compose **parent graphs** (Supervisor) and **child subgraphs** (Research, Analytics, Reporting) into a single, strongly-typed, observable, and testable AI system.

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

| Component        | Responsibility                                         |
|------------------|--------------------------------------------------------|
| Supervisor       | Orchestrates subgraphs, propagates shared state.       |
| Research Graph   | Decomposes objective, gathers findings.                |
| Analytics Graph  | Computes metrics, runs calculations.                   |
| Reporting Graph  | Composes the final report, validates quality.          |
| Input Guardrail  | Blocks prompt injection, jailbreaks, extraction.       |
| Output Guardrail | Redacts secrets, stack traces, internal details.       |

## Highlights

- **Strongly-typed state** via Pydantic v2 + TypedDict
- **Subgraph composition** with shared state propagation
- **Guardrails** for input and output safety
- **Observability** through structured logging, trace IDs, and LangSmith
- **CI/CD** with Ruff, Mypy, Pytest, and Docker
- **80%+ test coverage**, all LLM calls mocked

## Quick Start

```bash
# Install uv (https://github.com/astral-sh/uv)
uv sync

# Configure environment
cp .env.example .env
# edit .env and set OPENAI_API_KEY, LANGSMITH_API_KEY

# Run the application
uv run python app.py
```

## Documentation

- [Architecture](docs/architecture.md)
- [Setup Guide](docs/setup.md)
- [ADRs](docs/adr/)

## Testing

```bash
uv run pytest                 # all tests
uv run pytest --cov=app       # with coverage
uv run ruff check .
uv run mypy .
```

## License

MIT
