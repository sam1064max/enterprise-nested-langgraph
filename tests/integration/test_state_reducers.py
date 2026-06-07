"""Tests for GraphState reducers and helpers."""

from __future__ import annotations

from models.state import (
    _APPEND_METADATA_KEYS,
    _append,
    _merge_metadata,
    create_initial_state,
    generate_id,
    utc_now,
)


def test_append_with_single_value() -> None:
    assert _append([1, 2, 3], 4) == [1, 2, 3, 4]


def test_append_with_list_value() -> None:
    assert _append([1, 2, 3], [4, 5]) == [1, 2, 3, 4, 5]


def test_append_with_empty_existing() -> None:
    assert _append([], "x") == ["x"]


def test_append_with_empty_list_value() -> None:
    assert _append([1, 2], []) == [1, 2]


def test_merge_metadata_shallow_overwrite() -> None:
    merged = _merge_metadata({"a": 1, "b": 2}, {"b": 99, "c": 3})
    assert merged == {"a": 1, "b": 99, "c": 3}


def test_merge_metadata_with_none_right() -> None:
    merged = _merge_metadata({"a": 1}, None)
    assert merged == {"a": 1}


def test_merge_metadata_with_empty_dict_right() -> None:
    merged = _merge_metadata({"a": 1}, {})
    assert merged == {"a": 1}


def test_merge_metadata_appends_list_keys() -> None:
    merged = _merge_metadata(
        {"subgraph_timings": [{"name": "a"}]},
        {"subgraph_timings": [{"name": "b"}]},
    )
    assert merged["subgraph_timings"] == [{"name": "a"}, {"name": "b"}]


def test_merge_metadata_appends_state_transitions() -> None:
    merged = _merge_metadata(
        {"state_transitions": [{"from": "x", "to": "y"}]},
        {"state_transitions": [{"from": "y", "to": "z"}]},
    )
    assert merged["state_transitions"] == [
        {"from": "x", "to": "y"},
        {"from": "y", "to": "z"},
    ]


def test_merge_metadata_overwrites_non_list_keys() -> None:
    merged = _merge_metadata(
        {"guardrail_violations": [{"a": 1}]},
        {"guardrail_violations": [{"b": 2}]},
    )
    assert merged["guardrail_violations"] == [{"b": 2}]


def test_merge_metadata_replaces_existing_non_list_value() -> None:
    merged = _merge_metadata(
        {"foo": "scalar"},
        {"foo": ["a", "b"]},
    )
    assert merged["foo"] == ["a", "b"]


def test_append_metadata_keys_constant_contains_expected_keys() -> None:
    assert "subgraph_timings" in _APPEND_METADATA_KEYS
    assert "state_transitions" in _APPEND_METADATA_KEYS


def test_utc_now_is_timezone_aware() -> None:
    now = utc_now()
    assert now.tzinfo is not None


def test_generate_id_returns_string() -> None:
    assert isinstance(generate_id(), str)
    assert len(generate_id()) > 0


def test_generate_id_produces_unique_values() -> None:
    ids = {generate_id() for _ in range(50)}
    assert len(ids) == 50


def test_create_initial_state_has_required_fields() -> None:
    state = create_initial_state("hello")
    assert state["query"] == "hello"
    assert state["research_plan"] == []
    assert state["research_results"] == []
    assert state["analytics_results"] == []
    assert state["report"] == ""
    assert state["error"] is None
    assert state["status"] == "initialized"
    assert state["execution_time"] == 0.0
    assert state["metadata"]["subgraph_timings"] == []
    assert state["metadata"]["state_transitions"] == []


def test_create_initial_state_with_explicit_ids() -> None:
    state = create_initial_state("hi", request_id="r1", trace_id="t1")
    assert state["request_id"] == "r1"
    assert state["trace_id"] == "t1"


def test_create_initial_state_generates_distinct_ids() -> None:
    s1 = create_initial_state("a")
    s2 = create_initial_state("b")
    assert s1["request_id"] != s2["request_id"]
    assert s1["trace_id"] != s2["trace_id"]


def test_reducer_typed_dict_includes_required_keys() -> None:
    state = create_initial_state("schema check")
    required = {
        "query",
        "research_plan",
        "research_results",
        "analytics_results",
        "report",
        "metadata",
        "error",
        "trace_id",
        "request_id",
        "execution_time",
        "status",
    }
    assert required.issubset(state.keys())
