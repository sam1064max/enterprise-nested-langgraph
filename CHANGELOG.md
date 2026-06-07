# Changelog

All notable changes to the **Enterprise Nested LangGraph** project will
be documented in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* `tests/unit/test_tracing.py` — full coverage of the observability
  tracing module (id generation, LangSmith wiring, env handling).
* `tests/unit/test_calculator.py` — comprehensive coverage of the
  AST-based safe calculator.
* `Makefile` — ergonomics for `make test`, `make lint`, `make typecheck`.
* `CHANGELOG.md` — this file.

## [0.1.0] — 2026-06-07

### Added

* **Phase 0** — repository scaffolding.
* **Phase 1** — Pydantic v2 configuration management with custom YAML
  settings source (`config/settings.py`).
* **Phase 2** — shared `GraphState` TypedDict with custom reducers
  (`_append`, `_merge_metadata`).
* **Phase 3** — research subgraph (planner + executor) with in-memory
  search client.
* **Phase 4** — analytics subgraph (SQL agent + AST-safe calculator).
* **Phase 5** — reporting subgraph (writer + reviewer with quality
  thresholds).
* **Phase 6** — supervisor graph orchestrating all subgraphs.
* **Phase 7** — input and output guardrails (12 + 8 builtin patterns).
* **Phase 8** — observability layer (`structlog` JSON logging, request
  and trace ID generation, LangSmith wiring).
* **Phase 9** — comprehensive test suite: 140 unit and integration
  tests.
* **Phase 10** — architecture, setup, and ADR documentation.
* **Phase 11** — multi-stage Dockerfile, docker-compose, GitHub
  Actions CI workflow.

[Unreleased]: https://github.com/sam1064max/enterprise-nested-langgraph/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sam1064max/enterprise-nested-langgraph/releases/tag/v0.1.0
