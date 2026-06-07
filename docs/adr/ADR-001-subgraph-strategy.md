# ADR-001: Subgraph Composition Strategy

## Status

Accepted — 2026-06-07

## Context

LangGraph supports both flat and nested graph topologies. We needed a
design that allows independent development, testing, and reuse of
**Research**, **Analytics**, and **Reporting** concerns without
coupling them to the orchestrator.

## Decision

We adopt a **hierarchical (nested) topology**:

* The **Supervisor** is a top-level `StateGraph` that compiles three
  subgraphs as nodes via the `add_node("research", research_subgraph)`
  pattern.
* Each subgraph is itself a `StateGraph` and is exposed as a
  `CompiledStateGraph` for unit testing in isolation.
* All subgraphs share a single `GraphState` TypedDict; partial state
  updates are merged using custom reducers.

## Consequences

### Positive

* Subgraphs can be developed, versioned, and unit-tested in isolation.
* State contracts are explicit (`GraphState`) and type-checked with
  mypy.
* New subgraphs can be added by the supervisor without touching the
  existing ones.

### Negative

* Partial state updates rely on **reducers**, which add a small
  learning curve.
* A bug in the reducer semantics can silently corrupt state; mitigated
  by dedicated reducer unit tests (see `tests/integration/test_state_reducers.py`).
