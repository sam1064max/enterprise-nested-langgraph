# Architecture

## Overview

The **Enterprise Nested LangGraph** system is a hierarchical, multi-agent
research and analytics pipeline. It composes a top-level **Supervisor
Graph** with three **subgraphs** (Research, Analytics, Reporting) into a
single strongly-typed, observable, and testable AI system.

## High-Level Diagram

```
                     +----------------------------+
                     |        User Query          |
                     +-------------+--------------+
                                   |
                                   v
                     +----------------------------+
                     |      Input Guardrail       |
                     |  (length, prompt-injection)|
                     +-------------+--------------+
                                   |
                                   v
        +--------------------------------------------------+
        |                Supervisor Graph                  |
        |                                                  |
        |   +----------------+   +----------------+        |
        |   |   Research     |   |   Analytics    |  ...   |
        |   |   Subgraph     |-->|   Subgraph     |        |
        |   |                |   |                |        |
        |   | Planner        |   | SQL Agent      |        |
        |   | Executor       |   | Calculator     |        |
        |   +----------------+   +----------------+        |
        |              |                |                  |
        |              v                v                  |
        |          +-----------------------+               |
        |          |   Reporting Subgraph  |               |
        |          |                       |               |
        |          | Writer                |               |
        |          | Reviewer              |               |
        |          +-----------+-----------+               |
        |                      |                          |
        +----------------------+--------------------------+
                               |
                               v
                     +----------------------------+
                     |      Output Guardrail      |
                     |  (redact secrets, traces)  |
                     +-------------+--------------+
                                   |
                                   v
                     +----------------------------+
                     |      Final Report          |
                     +----------------------------+
```

## Module Map

```
enterprise-nested-langgraph/
├── app.py                      # Top-level entrypoint
├── config/
│   ├── config.yaml             # Default configuration
│   └── settings.py             # Pydantic v2 settings + env override
├── models/
│   ├── schemas.py              # Pydantic v2 domain models
│   └── state.py                # GraphState TypedDict + reducers
├── graphs/
│   ├── supervisor/graph.py     # Orchestrator
│   ├── research/               # Research subgraph
│   │   ├── planner.py
│   │   ├── executor.py
│   │   └── graph.py
│   ├── analytics/              # Analytics subgraph
│   │   ├── sql_agent.py
│   │   ├── calculator_agent.py
│   │   └── graph.py
│   └── reporting/              # Reporting subgraph
│       ├── writer.py
│       ├── reviewer.py
│       └── graph.py
├── tools/
│   ├── search.py               # In-memory search client
│   └── calculator.py           # AST-based safe calculator
├── guardrails/
│   ├── input_guardrail.py      # Input validation
│   └── output_guardrail.py     # Output redaction
├── observability/
│   ├── logging.py              # structlog JSON logging
│   └── tracing.py              # Request/trace IDs + LangSmith
└── tests/
    ├── unit/                   # 72 unit tests
    └── integration/            # 39 integration tests
```

## State Propagation

The system uses a single `GraphState` TypedDict as the contract between
the supervisor and all subgraphs. State fields are merged using two
custom reducers:

* **`_append`** — appends new items to list fields
  (`research_results`, `analytics_results`).
* **`_merge_metadata`** — shallowly merges dict fields, with a special
  case for list-typed metadata keys (`subgraph_timings`,
  `state_transitions`) which are appended.

This allows subgraphs to produce **partial state updates** that are
correctly merged into the supervisor's state.

## Subgraph Boundaries

Each subgraph is an independently compiled `StateGraph` exposed as a
`CompiledStateGraph` and consumed by the supervisor via the
`invoke()` / `stream()` API. Subgraphs are **stateless** across
invocations; all persistent state lives in `GraphState`.

## Error Handling

Errors raised inside a subgraph are caught by the supervisor's
`finalize` node, which records them under the `error` field and sets
`status = "failed"`. The pipeline never crashes the host process; the
caller is always given a state object.

## Observability

* **Structured logging** — `structlog` emits JSON logs to stdout. Every
  log line carries `app`, `level`, `timestamp`, and a request-scoped
  `request_id` / `trace_id` when configured.
* **Request/trace IDs** — `observability.tracing` generates UUIDs and
  wires them into LangSmith when `LANGSMITH_TRACING=true`.
* **Subgraph timings** — every node records its wall-clock duration in
  `metadata["subgraph_timings"]` for downstream dashboards.

## Guardrails

* **Input Guardrail** — rejects prompt-injection, jailbreak signatures,
  and over-long queries. Configurable via `config.yaml`.
* **Output Guardrail** — redacts API keys, AWS access keys, GitHub
  PATs, Google API keys, stack traces, internal markers, and any
  user-configured `KEY=VALUE` patterns from the final report.
