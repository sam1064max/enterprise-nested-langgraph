# Setup Guide

## Prerequisites

* Python 3.12+
* [uv](https://github.com/astral-sh/uv) (fast Python package manager)
* Git 2.30+

## Local Installation

```bash
# Clone the repository
git clone https://github.com/sam1064max/enterprise-nested-langgraph.git
cd enterprise-nested-langgraph

# Install dependencies into a project-local virtualenv
uv sync

# Copy the environment template
cp .env.example .env
# Edit .env and set required values (see Environment Variables below)
```

## Running the Application

```bash
# Run with the default query
uv run python app.py

# Run with a custom query
uv run python app.py "Compare two SaaS pricing models for 2026"
```

The application prints the final report to stdout. All intermediate
state (research findings, analytics results, metadata) is emitted as
JSON to stderr via `structlog`.

## Environment Variables

| Variable              | Required | Default | Description                                 |
|-----------------------|----------|---------|---------------------------------------------|
| `APP_ENV`             | No       | `dev`   | `dev` / `staging` / `prod`                  |
| `OPENAI_API_KEY`      | No       | (empty) | Only required if you wire real LLM calls    |
| `LANGCHAIN_TRACING_V2` | No      | `false` | Set to `true` to enable LangSmith tracing  |
| `LANGCHAIN_API_KEY`   | No       | (empty) | LangSmith API key                          |
| `LANGCHAIN_PROJECT`   | No       | (empty) | LangSmith project name                     |
| `GUARDRAILS_ENABLED`  | No       | `true`  | Toggle all guardrails off for benchmarking |

## Configuration File

Default configuration is loaded from `config/config.yaml`. The precedence
order is:

1. Constructor arguments to `AppSettings`
2. Environment variables
3. `.env` file
4. `config/config.yaml`

See `config/config.yaml` for the full set of knobs (logging format,
guardrail patterns, calculator limits, reviewer thresholds, etc.).

## Development Workflow

```bash
# Activate the virtualenv
source .venv/bin/activate          # Linux / macOS
.venv\Scripts\Activate.ps1         # Windows PowerShell

# Run tests
uv run pytest -q

# Lint
uv run ruff check .

# Type check
uv run mypy .

# Auto-fix lint errors
uv run ruff check . --fix
```

## Docker

A multi-stage Dockerfile and `docker-compose.yml` are provided. See
the repository root for details.

```bash
docker compose up --build
```

## Troubleshooting

* **"No module named 'langgraph'"** — Run `uv sync` to install
  dependencies.
* **Settings cache returns stale values** — Tests automatically
  reset the cache via the `reset_settings_cache` fixture; in ad-hoc
  scripts call `from config.settings import reset_settings_cache`
  followed by `reset_settings_cache()`.
* **Tests are slow** — The full suite runs in < 5 s on a developer
  laptop. If you see significantly longer times, check whether
  network-bound LLM calls have crept in (none should be present).
