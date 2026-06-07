# ADR-002: State Management with TypedDict + Reducers

## Status

Accepted — 2026-06-07

## Context

LangGraph requires a dict-like state container. Pydantic models are
*not* natively supported as a top-level state. We needed a single
source of truth that:

* supports **partial updates** (a subgraph may return a subset of
  fields),
* supports **list accumulation** (research and analytics both produce
  lists of results that must be merged across invocations),
* is **type-checked** with mypy,
* and is **lightweight** (no Pydantic validation on every read, only
  on writes).

## Decision

We use a `TypedDict` (`GraphState`) as the state contract and
implement two custom reducers:

* **`_append(left, right)`** — appends the right-hand value (or list)
  to the left-hand list. Used for `research_results` and
  `analytics_results`.
* **`_merge_metadata(left, right)`** — shallow-merges two dicts, with
  list-typed keys (`subgraph_timings`, `state_transitions`) appended
  rather than overwritten. All other keys are overwritten.

Domain Pydantic models live in `models/schemas.py` and are used to
**validate** values before they are written into the state.

## Consequences

### Positive

* State is a plain dict — fast, predictable, and easy to log.
* Reducers encode the merge semantics *once* in code, not in
  documentation.
* Pydantic schemas give us validation without coupling the runtime
  state to Pydantic.

### Negative

* Reducers must be `Callable[[Any, Any], Any]`-shaped, which mypy
  will not narrow; the reducer signatures use `Any` for the right
  operand.
* Runtime schema imports must be module-level (LangGraph resolves
  type hints at runtime); this forces the `from __future__ import
  annotations` boundary to exclude `GraphState`.
