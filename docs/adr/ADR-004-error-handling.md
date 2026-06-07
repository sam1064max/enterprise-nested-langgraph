# ADR-004: Error Handling and Guardrails

## Status

Accepted — 2026-06-07

## Context

Two distinct failure modes must be handled deliberately:

1. **User-supplied inputs** can be malicious (prompt injection,
   jailbreaks, PII, oversized payloads).
2. **Subgraph nodes** can raise exceptions (network errors, malformed
   data, downstream API failures).

A naive design would either let exceptions bubble up to the caller or
silently swallow them. Both are unacceptable for a production system.

## Decision

### Input Guardrail

* `InputGuardrail` runs **before** the supervisor and short-circuits
  the pipeline on failure. A rejection returns a state object with
  `error` set, `status = "rejected"`, and a human-readable
  `report` describing the rejection.
* Twelve built-in regex signatures cover common jailbreak and
  prompt-extraction patterns. Configured `block_patterns` extend the
  list.

### Output Guardrail

* `OutputGuardrail` runs **after** the supervisor. It redacts
  sensitive material from the final report *in place* and records the
  redaction categories in
  `metadata["output_redactions"]` for audit.

### Node Errors

* Every node in the supervisor and subgraphs is wrapped in a small
  try/except that records the error in `metadata["subgraph_timings"]`
  and propagates a partial state update. The supervisor's `finalize`
  node aggregates these into the top-level `error` field.

## Consequences

### Positive

* The host process never crashes on bad input or transient node
  errors.
* Audit trails (`output_redactions`, `subgraph_timings`) are first-class
  metadata fields.
* The rejection path is fully covered by integration tests.

### Negative

* Returning partial state on error complicates consumer code (callers
  must check `status` and `error` before assuming the report is
  valid).
* Regex-based detection is brittle; future iterations may swap in
  classifier-based detection.
