from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


QueryRow = dict[str, Any]
QueryRows = list[QueryRow]


class QueryResult(list[QueryRow]):
    def __init__(
        self,
        rows: QueryRows,
        *,
        columns: list[str] | None = None,
        source: str = "unknown",
        message: str | None = None,
    ) -> None:
        super().__init__(rows)
        self.columns = columns or _columns_from_rows(rows)
        self.source = source
        self.message = message

    def mappings(self) -> "QueryResult":
        return self


@dataclass(frozen=True)
class DatabaseConnection:
    name: str
    status: str | None = None
    payload: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DatabaseConnection":
        return cls(
            name=str(payload.get("name") or payload.get("Name") or ""),
            status=payload.get("status") or payload.get("Status"),
            payload=payload,
        )


class DbTransport(Protocol):
    db_get_connections_path: str
    db_get_connection_info_path: str
    db_add_datasource_path: str
    db_set_datasource_connect_url_path: str
    db_set_datasource_enabled_path: str
    db_set_datasource_max_connections_path: str
    db_remove_datasource_path: str
    db_begin_transaction_path: str
    db_commit_transaction_path: str
    db_rollback_transaction_path: str
    db_close_transaction_path: str
    db_run_query_path: str
    db_run_scalar_query_path: str
    db_run_scalar_prep_query_path: str
    db_run_prep_query_path: str
    db_run_prep_update_path: str
    db_run_update_query_path: str
    db_run_named_query_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class DbClientMixin:
    def db_get_connections(self: DbTransport) -> list[DatabaseConnection]:
        response = self._post(self.db_get_connections_path, {})
        connections = response.get("connections")
        if not isinstance(connections, list):
            from fluxy.client import FluxyError

            raise FluxyError("getConnections response missing `connections` list")
        return [DatabaseConnection.from_payload(connection) for connection in connections]

    def db_get_connection_info(self: DbTransport, name: str) -> dict[str, Any]:
        response = self._post(self.db_get_connection_info_path, {"name": name})
        info = response.get("info")
        if not isinstance(info, dict):
            from fluxy.client import FluxyError

            raise FluxyError("getConnectionInfo response missing `info` object")
        return dict(info)

    def db_add_datasource(
        self: DbTransport,
        name: str,
        connect_url: str,
        *,
        jdbc_driver: str = "SQLite",
        description: str = "Fluxy-managed datasource",
        username: str = "",
        password: str = "",
        props: str = "",
        validation_query: str = "SELECT 1",
        max_connections: int = 8,
    ) -> bool:
        response = self._post(
            self.db_add_datasource_path,
            {
                "jdbcDriver": jdbc_driver,
                "name": name,
                "description": description,
                "connectUrl": connect_url,
                "username": username,
                "password": password,
                "props": props,
                "validationQuery": validation_query,
                "maxConnections": max_connections,
            },
        )
        return bool(response.get("ok"))

    def db_set_datasource_connect_url(
        self: DbTransport,
        name: str,
        connect_url: str,
    ) -> bool:
        response = self._post(
            self.db_set_datasource_connect_url_path,
            {"name": name, "connectUrl": connect_url},
        )
        return bool(response.get("ok"))

    def db_set_datasource_enabled(
        self: DbTransport,
        name: str,
        enabled: bool,
    ) -> bool:
        response = self._post(
            self.db_set_datasource_enabled_path,
            {"name": name, "enabled": enabled},
        )
        return bool(response.get("ok"))

    def db_set_datasource_max_connections(
        self: DbTransport,
        name: str,
        max_connections: int,
    ) -> bool:
        response = self._post(
            self.db_set_datasource_max_connections_path,
            {"name": name, "maxConnections": max_connections},
        )
        return bool(response.get("ok"))

    def db_remove_datasource(self: DbTransport, name: str) -> bool:
        response = self._post(self.db_remove_datasource_path, {"name": name})
        return bool(response.get("ok"))

    def db_begin_transaction(
        self: DbTransport,
        database: str,
        isolation_level: int | None = None,
        timeout: int | None = None,
    ) -> str:
        payload: dict[str, Any] = {"database": database}
        if isolation_level is not None:
            payload["isolationLevel"] = isolation_level
        if timeout is not None:
            payload["timeout"] = timeout
        response = self._post(self.db_begin_transaction_path, payload)
        return str(response.get("tx"))

    def db_commit_transaction(self: DbTransport, tx: str) -> bool:
        response = self._post(self.db_commit_transaction_path, {"tx": tx})
        return bool(response.get("ok"))

    def db_rollback_transaction(self: DbTransport, tx: str) -> bool:
        response = self._post(self.db_rollback_transaction_path, {"tx": tx})
        return bool(response.get("ok"))

    def db_close_transaction(self: DbTransport, tx: str) -> bool:
        response = self._post(self.db_close_transaction_path, {"tx": tx})
        return bool(response.get("ok"))

    def db_run_query(
        self: DbTransport,
        query: str,
        database: str | None = None,
        tx: str | None = None,
    ) -> QueryResult:
        payload: dict[str, Any] = {"query": query}
        if database is not None:
            payload["database"] = database
        if tx is not None:
            payload["tx"] = tx
        response = self._post(self.db_run_query_path, payload)
        return query_result_from_response(response)

    def db_run_scalar_query(
        self: DbTransport,
        query: str,
        database: str | None = None,
        args: list[Any] | None = None,
    ) -> Any:
        payload: dict[str, Any] = {"query": query}
        if database is not None:
            payload["database"] = database
        if args is not None:
            payload["args"] = args
        response = self._post(self.db_run_scalar_query_path, payload)
        return response.get("value")

    def db_run_scalar_prep_query(
        self: DbTransport,
        query: str,
        args: list[Any] | None = None,
        database: str | None = None,
    ) -> Any:
        payload: dict[str, Any] = {"query": query, "args": args or []}
        if database is not None:
            payload["database"] = database
        response = self._post(self.db_run_scalar_prep_query_path, payload)
        return response.get("value")

    def db_run_prep_query(
        self: DbTransport,
        query: str,
        args: list[Any] | None = None,
        database: str | None = None,
    ) -> QueryResult:
        payload: dict[str, Any] = {"query": query, "args": args or []}
        if database is not None:
            payload["database"] = database
        response = self._post(self.db_run_prep_query_path, payload)
        return query_result_from_response(response)

    def db_run_prep_update(
        self: DbTransport,
        query: str,
        args: list[Any] | None = None,
        database: str | None = None,
        *,
        get_key: bool = False,
        skip_audit: bool = False,
    ) -> Any:
        payload: dict[str, Any] = {
            "query": query,
            "args": args or [],
            "getKey": get_key,
            "skipAudit": skip_audit,
        }
        if database is not None:
            payload["database"] = database
        response = self._post(self.db_run_prep_update_path, payload)
        return response.get("value")

    def db_run_update_query(
        self: DbTransport,
        query: str,
        database: str | None = None,
        tx: str | None = None,
        *,
        get_key: bool = False,
        skip_audit: bool = False,
    ) -> Any:
        payload: dict[str, Any] = {
            "query": query,
            "getKey": get_key,
            "skipAudit": skip_audit,
        }
        if database is not None:
            payload["database"] = database
        if tx is not None:
            payload["tx"] = tx
        response = self._post(self.db_run_update_query_path, payload)
        return response.get("value")

    def db_run_named_query(
        self: DbTransport,
        path: str,
        parameters: dict[str, Any] | None = None,
        project: str | None = None,
    ) -> QueryResult:
        payload: dict[str, Any] = {"path": path, "parameters": parameters or {}}
        if project is not None:
            payload["project"] = project
        response = self._post(self.db_run_named_query_path, payload)
        return query_result_from_response(response)


def query_rows_from_payload(result: Any) -> QueryRows:
    if not isinstance(result, list):
        from fluxy.client import FluxyError

        raise FluxyError("runNamedQuery response must be a list of row objects")
    rows: QueryRows = []
    for row in result:
        if not isinstance(row, dict):
            from fluxy.client import FluxyError

            raise FluxyError("runNamedQuery response rows must be objects")
        rows.append(dict(row))
    return rows


def query_result_from_response(response: dict[str, Any]) -> QueryResult:
    result = response.get("result")
    if isinstance(result, dict) and "columns" in result and "rows" in result:
        columns = query_columns_from_payload(result.get("columns"))
        rows = query_rows_from_wire(result.get("rows"), columns)
    else:
        rows = query_rows_from_payload(result)
        response_columns = response.get("columns")
        columns = query_columns_from_payload(response_columns) if response_columns is not None else None
    source = response.get("resultSource") or response.get("source") or "gateway"
    message = response.get("resultMessage") or response.get("message")
    return QueryResult(
        rows,
        columns=columns,
        source=str(source),
        message=str(message) if message is not None else None,
    )


def query_columns_from_payload(columns: Any) -> list[str]:
    if not isinstance(columns, list):
        from fluxy.client import FluxyError

        raise FluxyError("runNamedQuery dataset columns must be a list")
    return [str(column) for column in columns]


def query_rows_from_wire(rows: Any, columns: list[str]) -> QueryRows:
    if not isinstance(rows, list):
        from fluxy.client import FluxyError

        raise FluxyError("runNamedQuery dataset rows must be a list")
    mapped_rows: QueryRows = []
    for row in rows:
        if not isinstance(row, list):
            from fluxy.client import FluxyError

            raise FluxyError("runNamedQuery dataset rows must be lists")
        if len(row) != len(columns):
            from fluxy.client import FluxyError

            raise FluxyError("runNamedQuery dataset row width must match columns")
        mapped_rows.append(dict(zip(columns, row, strict=True)))
    return mapped_rows


def _columns_from_rows(rows: QueryRows) -> list[str]:
    if not rows:
        return []
    return list(rows[0].keys())
