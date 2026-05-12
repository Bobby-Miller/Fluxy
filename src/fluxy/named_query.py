from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, TypedDict

from fluxy.client.db import QueryResult


NamedQuerySqlType = Literal[
    "Int1",
    "Int2",
    "Int4",
    "Int8",
    "Float4",
    "Float8",
    "Boolean",
    "String",
    "DateTime",
    "ByteArray",
]


class NamedQueryParameter(TypedDict):
    type: Literal["Parameter"]
    identifier: str
    sqlType: int


class NamedQueryRunner(Protocol):
    def run_named_query(
        self,
        project_location: Path,
        path: str,
        *,
        parameters: dict[str, Any] | None = None,
        project: str | None = None,
    ) -> QueryResult: ...


NAMED_QUERY_ROOT = Path("ignition") / "named-query"
SAFE_PART = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Observed from an Ignition Designer named query parameter sample.
NAMED_QUERY_SQL_TYPES: dict[NamedQuerySqlType, int] = {
    "Int1": 0,
    "Int2": 1,
    "Int4": 2,
    "Int8": 3,
    "Float4": 4,
    "Float8": 5,
    "Boolean": 6,
    "String": 7,
    "DateTime": 8,
    "ByteArray": 20,
}


def add_named_query(
    project_path: str | Path,
    name: str,
    query: str,
    *,
    database: str = "",
    parameters: list[dict[str, Any]] | None = None,
) -> Path:
    target = named_query_path(project_path, name)
    target.mkdir(parents=True, exist_ok=True)
    (target / "query.sql").write_text(query.rstrip() + "\n", encoding="utf-8")
    (target / "resource.json").write_text(
        json.dumps(named_query_resource(database=database, parameters=parameters or []), indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def delete_named_query(project_path: str | Path, name: str) -> Path:
    target = named_query_path(project_path, name)
    if target.exists():
        shutil.rmtree(target)
    return target


def named_query_path(project_path: str | Path, name: str) -> Path:
    return Path(project_path) / NAMED_QUERY_ROOT / safe_named_query_relative_path(name)


def read_named_query_sql(project_path: str | Path, name: str) -> str:
    return (named_query_path(project_path, name) / "query.sql").read_text(encoding="utf-8")


def safe_named_query_relative_path(name: str) -> Path:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("named query name must stay inside ignition/named-query")
    if any(not SAFE_PART.match(part) for part in path.parts):
        raise ValueError("named query path parts must be Python identifiers")
    return path


def named_query_parameter(identifier: str, sql_type: NamedQuerySqlType | int) -> NamedQueryParameter:
    if isinstance(sql_type, str):
        try:
            sql_type = NAMED_QUERY_SQL_TYPES[sql_type]
        except KeyError as exc:
            raise ValueError("Unknown named query sql type: %s" % sql_type) from exc
    return {"type": "Parameter", "identifier": identifier, "sqlType": sql_type}


def named_query_resource(database: str = "", parameters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "useMaxReturnSize": False,
        "autoBatchEnabled": False,
        "fallbackValue": "",
        "maxReturnSize": 100,
        "cacheUnit": "SEC",
        "type": "Query",
        "enabled": True,
        "cacheAmount": 1,
        "cacheEnabled": False,
        "database": database,
        "fallbackEnabled": False,
        "permissions": [{"zone": "", "role": ""}],
        "lastModification": {
            "actor": "fluxy.named_query",
            "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        },
    }
    if parameters:
        attributes["parameters"] = parameters
    return {
        "scope": "DG",
        "version": 2,
        "restricted": False,
        "overridable": True,
        "files": ["query.sql"],
        "attributes": attributes,
    }
