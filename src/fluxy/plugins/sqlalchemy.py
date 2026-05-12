from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fluxy.client.db import QueryResult, QueryRows
from fluxy.named_query import read_named_query_sql


class SQLAlchemyNamedQueryRunner:
    def __init__(self, engine: Any, *, text_factory: Callable[[str], Any] | None = None) -> None:
        self.engine = engine
        self.text_factory = text_factory

    def run_named_query(
        self,
        project_location: Path,
        path: str,
        *,
        parameters: dict[str, Any] | None = None,
        project: str | None = None,
    ) -> QueryResult:
        del project
        statement = self._text(read_named_query_sql(project_location, path))
        with self.engine.begin() as connection:
            result = connection.execute(statement, parameters or {})
            return _query_result(result)

    def _text(self, sql: str) -> Any:
        if self.text_factory is not None:
            return self.text_factory(sql)
        try:
            from sqlalchemy import text
        except ImportError as exc:
            raise RuntimeError(
                "SQLAlchemyNamedQueryRunner requires SQLAlchemy to be installed by the application"
            ) from exc
        return text(sql)


def _rows_to_dicts(result: Any) -> QueryRows:
    if hasattr(result, "mappings"):
        return [dict(row) for row in result.mappings().all()]
    if hasattr(result, "keys"):
        keys = list(result.keys())
        return [dict(zip(keys, row, strict=True)) for row in result.fetchall()]
    return [dict(row) for row in result]


def _query_result(result: Any) -> QueryResult:
    rows = _rows_to_dicts(result)
    columns = [str(column) for column in result.keys()] if hasattr(result, "keys") else None
    return QueryResult(
        rows,
        columns=columns,
        source="sqlalchemy",
        message="SQLAlchemy Result converted to Fluxy row mappings",
    )
