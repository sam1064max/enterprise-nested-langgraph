"""SQL agent.

A minimal SQL agent that runs read-only SQL queries against an
in-memory tabular dataset. The default dataset is a small SaaS metrics
fixture so the agent can run end-to-end without any external
database. Production deployments can inject a different dataset or
swap in a real SQLAlchemy engine.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

_FORBIDDEN_KEYWORDS: frozenset[str] = frozenset(
    {
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "replace",
        "truncate",
        "attach",
        "detach",
        "pragma",
        "vacuum",
        "reindex",
    }
)


@dataclass
class SQLResult:
    """Outcome of a SQL execution."""

    columns: list[str] = field(default_factory=list)
    rows: list[tuple[Any, ...]] = field(default_factory=list)
    row_count: int = 0
    error: str | None = None
    query: str = ""


class _SQLValidationError(ValueError):
    """Raised when a query is rejected by the safety filter."""


class _DictRow:
    """Lightweight dict-like row used for the default dataset."""

    def __init__(self, data: Mapping[str, Any]) -> None:
        self._data: dict[str, Any] = dict(data)

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401
        return self._data[key]

    def __iter__(self) -> Any:  # noqa: ANN401
        return iter(self._data)

    def keys(self) -> Any:  # noqa: ANN401
        return self._data.keys()

    def values(self) -> list[Any]:
        return list(self._data.values())

    def _asdict(self) -> dict[str, Any]:
        return dict(self._data)


def _build_default_dataset() -> dict[str, list[_DictRow]]:
    months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]
    arr_rows: list[_DictRow] = []
    for index, month in enumerate(months):
        arr_rows.append(
            _DictRow(
                {
                    "month": month,
                    "arr": 1_000_000.0 + index * 75_000.0,
                    "customers": 100 + index * 8,
                    "logo_churn_pct": 2.1 - index * 0.1,
                }
            )
        )
    plan_rows = [
        _DictRow({"plan": "starter", "price_usd": 49.0, "seats": 25}),
        _DictRow({"plan": "growth", "price_usd": 199.0, "seats": 75}),
        _DictRow({"plan": "enterprise", "price_usd": 999.0, "seats": 250}),
    ]
    return {"monthly_arr": arr_rows, "plans": plan_rows}


_DEFAULT_DATASET: dict[str, list[_DictRow]] = _build_default_dataset()


class SQLAgent:
    """Execute read-only SQL against a fixed in-memory dataset."""

    def __init__(self, dataset: Mapping[str, list[_DictRow]] | None = None) -> None:
        if dataset is None:
            dataset = _DEFAULT_DATASET
        self._connection = sqlite3.connect(":memory:")
        self._connection.row_factory = sqlite3.Row
        self._load_dataset(dataset)

    def _load_dataset(self, dataset: Mapping[str, list[_DictRow]]) -> None:
        for table, rows in dataset.items():
            if not rows:
                continue
            first = rows[0]
            columns = list(first._asdict().keys())
            placeholders = ", ".join(["?"] * len(columns))
            column_list = ", ".join(columns)
            self._connection.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ({column_list})"
            )  # fmt: skip
            self._connection.executemany(
                f"INSERT INTO {table} VALUES ({placeholders})",  # noqa: S608
                [tuple(r) for r in rows],
            )
        self._connection.commit()

    def run(self, query: str) -> SQLResult:
        """Execute a read-only SQL query.

        Args:
            query: A SQL query string. Only ``SELECT`` and ``WITH``
                statements are permitted.

        Returns:
            A :class:`SQLResult` with columns, rows, and metadata.
        """
        cleaned = query.strip().rstrip(";")
        if not cleaned:
            return SQLResult(error="empty query", query=query)

        try:
            self._validate(cleaned)
        except _SQLValidationError as exc:
            return SQLResult(error=str(exc), query=query)

        try:
            cursor = self._connection.execute(cleaned)
        except sqlite3.Error as exc:
            return SQLResult(error=f"sql error: {exc}", query=query)

        rows = cursor.fetchall()
        description = cursor.description
        return SQLResult(
            columns=[d[0] for d in description] if description else [],
            rows=[tuple(r) for r in rows],
            row_count=len(rows),
            query=cleaned,
        )

    @staticmethod
    def _validate(query: str) -> None:
        head = re.split(r"\s+", query, maxsplit=1)[0].lower()
        if head not in {"select", "with"}:
            raise _SQLValidationError(f"only SELECT/WITH queries are allowed; got {head!r}")
        lowered = query.lower()
        for keyword in _FORBIDDEN_KEYWORDS:
            pattern = r"\b" + keyword + r"\b"
            if re.search(pattern, lowered):
                raise _SQLValidationError(f"forbidden keyword detected: {keyword}")


__all__ = ["SQLAgent", "SQLResult"]
