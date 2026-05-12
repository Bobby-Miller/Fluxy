from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


GET_CONNECTIONS_POST = COMMON + r'''


def _connection_to_dict(row):
    item = {}
    for key in ["Name", "name", "Status", "status", "Driver", "driver"]:
        try:
            value = row[key]
        except Exception:
            continue
        if value is not None:
            item[key] = str(value)
    if "name" not in item and "Name" in item:
        item["name"] = item["Name"]
    if "status" not in item and "Status" in item:
        item["status"] = item["Status"]
    return item


def doPost(request, session):
    operation = "Db.getConnections"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        connections = [_connection_to_dict(row) for row in system.db.getConnections()]
        _log_success(operation)
        return {"json": {"ok": True, "connections": connections}}
    except Exception, exc:
        _log_error(operation, "getConnections failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

GET_CONNECTION_INFO_POST = COMMON + r'''


def _read_value(item, key):
    try:
        return item[key]
    except Exception:
        pass
    try:
        return getattr(item, key)
    except Exception:
        pass
    return None


def _connection_info_to_dict(info):
    if hasattr(info, "getColumnNames") and hasattr(info, "getRowCount"):
        column_names = list(info.getColumnNames())
        if info.getRowCount() > 0:
            item = {}
            for column_name in column_names:
                value = info.getValueAt(0, column_name)
                if value is not None:
                    item[str(column_name)] = value if isinstance(value, bool) else str(value)
            return item
    if hasattr(info, "getUnderlyingDataset"):
        return _connection_info_to_dict(info.getUnderlyingDataset())
    try:
        if len(info) > 0:
            return _connection_info_to_dict(info[0])
    except Exception:
        pass
    item = {}
    for key in [
        "Name",
        "name",
        "Status",
        "status",
        "Driver",
        "driver",
        "ConnectURL",
        "connectURL",
        "connectUrl",
        "URL",
        "url",
        "Username",
        "username",
        "ValidationQuery",
        "validationQuery",
        "Enabled",
        "enabled",
    ]:
        value = _read_value(info, key)
        if value is not None:
            item[key] = value if isinstance(value, bool) else str(value)
    if "name" not in item and "Name" in item:
        item["name"] = item["Name"]
    if "status" not in item and "Status" in item:
        item["status"] = item["Status"]
    if not item:
        item["raw"] = str(info)
    return item


def doPost(request, session):
    operation = "Db.getConnectionInfo"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        name = payload.get("name")
        if not isinstance(name, basestring):
            return _bad_request("Request must include name string", _request_debug(request))
        info = _connection_info_to_dict(system.db.getConnectionInfo(name))
        _log_success(operation)
        return {"json": {"ok": True, "info": info}}
    except Exception, exc:
        _log_error(operation, "getConnectionInfo failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

ADD_DATASOURCE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.addDatasource"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        jdbc_driver = payload.get("jdbcDriver") or payload.get("jdbc_driver") or "SQLite"
        name = payload.get("name")
        description = payload.get("description") or "Fluxy-managed datasource"
        connect_url = payload.get("connectUrl") or payload.get("connectURL") or payload.get("connect_url")
        username = payload.get("username") or ""
        password = payload.get("password") or ""
        props = payload.get("props") or ""
        validation_query = payload.get("validationQuery") or payload.get("validation_query") or "SELECT 1"
        max_connections = payload.get("maxConnections") or payload.get("max_connections") or 8
        if not isinstance(jdbc_driver, basestring):
            return _bad_request("jdbcDriver must be a string", _request_debug(request))
        if not isinstance(name, basestring):
            return _bad_request("Request must include name string", _request_debug(request))
        if not isinstance(connect_url, basestring):
            return _bad_request("Request must include connectUrl string", _request_debug(request))
        system.db.addDatasource(
            jdbc_driver,
            name,
            description,
            connect_url,
            username,
            password,
            props,
            validation_query,
            int(max_connections),
        )
        _log_success(operation)
        return {"json": {"ok": True, "name": name}}
    except Exception, exc:
        _log_error(operation, "addDatasource failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

SET_DATASOURCE_CONNECT_URL_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.setDatasourceConnectURL"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        name = payload.get("name")
        connect_url = payload.get("connectUrl") or payload.get("connectURL") or payload.get("connect_url")
        if not isinstance(name, basestring):
            return _bad_request("Request must include name string", _request_debug(request))
        if not isinstance(connect_url, basestring):
            return _bad_request("Request must include connectUrl string", _request_debug(request))
        system.db.setDatasourceConnectURL(name, connect_url)
        _log_success(operation)
        return {"json": {"ok": True, "name": name, "connectUrl": connect_url}}
    except Exception, exc:
        _log_error(operation, "setDatasourceConnectURL failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

SET_DATASOURCE_ENABLED_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.setDatasourceEnabled"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        name = payload.get("name")
        enabled = payload.get("enabled")
        if not isinstance(name, basestring):
            return _bad_request("Request must include name string", _request_debug(request))
        if not isinstance(enabled, bool):
            return _bad_request("Request must include enabled boolean", _request_debug(request))
        system.db.setDatasourceEnabled(name, enabled)
        _log_success(operation)
        return {"json": {"ok": True, "name": name, "enabled": enabled}}
    except Exception, exc:
        _log_error(operation, "setDatasourceEnabled failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

SET_DATASOURCE_MAX_CONNECTIONS_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.setDatasourceMaxConnections"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        name = payload.get("name")
        max_connections = payload.get("maxConnections") or payload.get("max_connections") or payload.get("maxActive") or payload.get("max_active")
        if not isinstance(name, basestring):
            return _bad_request("Request must include name string", _request_debug(request))
        if max_connections is None:
            return _bad_request("Request must include maxConnections", _request_debug(request))
        system.db.setDatasourceMaxConnections(name, int(max_connections))
        _log_success(operation)
        return {"json": {"ok": True, "name": name, "maxConnections": int(max_connections)}}
    except Exception, exc:
        _log_error(operation, "setDatasourceMaxConnections failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

REMOVE_DATASOURCE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.removeDatasource"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        name = payload.get("name")
        if not isinstance(name, basestring):
            return _bad_request("Request must include name string", _request_debug(request))
        system.db.removeDatasource(name)
        _log_success(operation)
        return {"json": {"ok": True, "name": name}}
    except Exception, exc:
        _log_error(operation, "removeDatasource failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

BEGIN_TRANSACTION_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.beginTransaction"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        database = payload.get("database") or payload.get("datasource")
        isolation_level = payload.get("isolationLevel") or payload.get("isolation_level")
        timeout = payload.get("timeout")
        if not isinstance(database, basestring):
            return _bad_request("Request must include database string", _request_debug(request))
        if isolation_level is not None and timeout is not None:
            tx = system.db.beginTransaction(database, int(isolation_level), int(timeout))
        elif isolation_level is not None:
            tx = system.db.beginTransaction(database, int(isolation_level))
        elif timeout is not None:
            tx = system.db.beginTransaction(database, timeout=int(timeout))
        else:
            tx = system.db.beginTransaction(database)
        _log_success(operation)
        return {"json": {"ok": True, "tx": tx}}
    except Exception, exc:
        _log_error(operation, "beginTransaction failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

COMMIT_TRANSACTION_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.commitTransaction"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        tx = payload.get("tx")
        if not isinstance(tx, basestring):
            return _bad_request("Request must include tx string", _request_debug(request))
        system.db.commitTransaction(tx)
        _log_success(operation)
        return {"json": {"ok": True, "tx": tx}}
    except Exception, exc:
        _log_error(operation, "commitTransaction failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

ROLLBACK_TRANSACTION_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.rollbackTransaction"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        tx = payload.get("tx")
        if not isinstance(tx, basestring):
            return _bad_request("Request must include tx string", _request_debug(request))
        system.db.rollbackTransaction(tx)
        _log_success(operation)
        return {"json": {"ok": True, "tx": tx}}
    except Exception, exc:
        _log_error(operation, "rollbackTransaction failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

CLOSE_TRANSACTION_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.closeTransaction"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        tx = payload.get("tx")
        if not isinstance(tx, basestring):
            return _bad_request("Request must include tx string", _request_debug(request))
        system.db.closeTransaction(tx)
        _log_success(operation)
        return {"json": {"ok": True, "tx": tx}}
    except Exception, exc:
        _log_error(operation, "closeTransaction failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RUN_SCALAR_QUERY_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.runScalarQuery"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        query = payload.get("query")
        database = payload.get("database") or payload.get("datasource")
        args = payload.get("args")
        if not isinstance(query, basestring):
            return _bad_request("Request must include query string", _request_debug(request))
        if args is not None and not isinstance(args, list):
            return _bad_request("args must be a list", _request_debug(request))
        if args:
            value = system.db.runScalarPrepQuery(query, args, database) if database else system.db.runScalarPrepQuery(query, args)
        else:
            value = system.db.runScalarQuery(query, database) if database else system.db.runScalarQuery(query)
        _log_success(operation)
        return {"json": {"ok": True, "value": value}}
    except Exception, exc:
        _log_error(operation, "runScalarQuery failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RUN_QUERY_POST = COMMON + r'''


def _dataset_to_wire(dataset):
    rows = []
    column_names = list(dataset.getColumnNames())
    for row_index in range(dataset.getRowCount()):
        row = []
        for column_name in column_names:
            row.append(dataset.getValueAt(row_index, column_name))
        rows.append(row)
    return {
        "rows": rows,
        "columns": column_names,
    }


def doPost(request, session):
    operation = "Db.runQuery"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        query = payload.get("query")
        database = payload.get("database") or payload.get("datasource")
        tx = payload.get("tx")
        if not isinstance(query, basestring):
            return _bad_request("Request must include query string", _request_debug(request))
        if tx:
            result = system.db.runQuery(query, database or "", tx)
        elif database:
            result = system.db.runQuery(query, database)
        else:
            result = system.db.runQuery(query)
        result = _dataset_to_wire(result)
        _log_success(operation)
        return {
            "json": {
                "ok": True,
                "result": result,
                "resultSource": "ignition.dataset",
                "resultMessage": "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings",
            }
        }
    except Exception, exc:
        _log_error(operation, "runQuery failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RUN_SCALAR_PREP_QUERY_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.runScalarPrepQuery"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        query = payload.get("query")
        args = payload.get("args") or []
        database = payload.get("database") or payload.get("datasource")
        if not isinstance(query, basestring):
            return _bad_request("Request must include query string", _request_debug(request))
        if not isinstance(args, list):
            return _bad_request("args must be a list", _request_debug(request))
        value = system.db.runScalarPrepQuery(query, args, database) if database else system.db.runScalarPrepQuery(query, args)
        _log_success(operation)
        return {"json": {"ok": True, "value": value}}
    except Exception, exc:
        _log_error(operation, "runScalarPrepQuery failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RUN_PREP_QUERY_POST = COMMON + r'''


def _dataset_to_wire(dataset):
    rows = []
    column_names = list(dataset.getColumnNames())
    for row_index in range(dataset.getRowCount()):
        row = []
        for column_name in column_names:
            row.append(dataset.getValueAt(row_index, column_name))
        rows.append(row)
    return {
        "rows": rows,
        "columns": column_names,
    }


def doPost(request, session):
    operation = "Db.runPrepQuery"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        query = payload.get("query")
        args = payload.get("args") or []
        database = payload.get("database") or payload.get("datasource")
        if not isinstance(query, basestring):
            return _bad_request("Request must include query string", _request_debug(request))
        if not isinstance(args, list):
            return _bad_request("args must be a list", _request_debug(request))
        result = system.db.runPrepQuery(query, args, database) if database else system.db.runPrepQuery(query, args)
        result = _dataset_to_wire(result)
        _log_success(operation)
        return {
            "json": {
                "ok": True,
                "result": result,
                "resultSource": "ignition.dataset",
                "resultMessage": "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings",
            }
        }
    except Exception, exc:
        _log_error(operation, "runPrepQuery failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RUN_PREP_UPDATE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.runPrepUpdate"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        query = payload.get("query")
        args = payload.get("args") or []
        database = payload.get("database") or payload.get("datasource")
        get_key = bool(payload.get("getKey") or payload.get("get_key"))
        skip_audit = bool(payload.get("skipAudit") or payload.get("skip_audit"))
        if not isinstance(query, basestring):
            return _bad_request("Request must include query string", _request_debug(request))
        if not isinstance(args, list):
            return _bad_request("args must be a list", _request_debug(request))
        if database:
            value = system.db.runPrepUpdate(query, args, database, "", get_key, skip_audit)
        elif get_key or skip_audit:
            value = system.db.runPrepUpdate(query, args, "", "", get_key, skip_audit)
        else:
            value = system.db.runPrepUpdate(query, args)
        _log_success(operation)
        return {"json": {"ok": True, "value": value}}
    except Exception, exc:
        _log_error(operation, "runPrepUpdate failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RUN_UPDATE_QUERY_POST = COMMON + r'''


def doPost(request, session):
    operation = "Db.runUpdateQuery"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        query = payload.get("query")
        database = payload.get("database") or payload.get("datasource")
        tx = payload.get("tx")
        get_key = bool(payload.get("getKey") or payload.get("get_key"))
        skip_audit = bool(payload.get("skipAudit") or payload.get("skip_audit"))
        if not isinstance(query, basestring):
            return _bad_request("Request must include query string", _request_debug(request))
        if tx:
            value = system.db.runUpdateQuery(query, database or "", tx, get_key, skip_audit)
        elif database:
            value = system.db.runUpdateQuery(query, database, "", get_key, skip_audit)
        elif get_key or skip_audit:
            value = system.db.runUpdateQuery(query, "", "", get_key, skip_audit)
        else:
            value = system.db.runUpdateQuery(query)
        _log_success(operation)
        return {"json": {"ok": True, "value": value}}
    except Exception, exc:
        _log_error(operation, "runUpdateQuery failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RUN_NAMED_QUERY_POST = COMMON + r'''


def _dataset_to_wire(dataset):
    rows = []
    column_names = list(dataset.getColumnNames())
    for row_index in range(dataset.getRowCount()):
        row = []
        for column_name in column_names:
            row.append(dataset.getValueAt(row_index, column_name))
        rows.append(row)
    return {
        "rows": rows,
        "columns": column_names,
    }


def doPost(request, session):
    operation = "Db.runNamedQuery"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        path = payload.get("path")
        parameters = payload.get("parameters") or {}
        project = payload.get("project")
        if not isinstance(path, basestring):
            return _bad_request("Request must include path string", _request_debug(request))
        if not isinstance(parameters, dict):
            return _bad_request("parameters must be an object", _request_debug(request))
        if project:
            result = system.db.runNamedQuery(project, path, parameters)
        else:
            result = system.db.runNamedQuery(path, parameters)
        source = "ignition"
        message = None
        if hasattr(result, "getColumnNames") and hasattr(result, "getRowCount"):
            result = _dataset_to_wire(result)
            source = "ignition.dataset"
            message = "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings"
        _log_success(operation)
        return {"json": {"ok": True, "result": result, "resultSource": source, "resultMessage": message}}
    except Exception, exc:
        _log_error(operation, "runNamedQuery failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RESOURCES = [
    WebDevResource("db/getConnections", "db/getConnections", GET_CONNECTIONS_POST),
    WebDevResource("db/getConnectionInfo", "db/getConnectionInfo", GET_CONNECTION_INFO_POST),
    WebDevResource("db/addDatasource", "db/addDatasource", ADD_DATASOURCE_POST),
    WebDevResource(
        "db/setDatasourceConnectURL",
        "db/setDatasourceConnectURL",
        SET_DATASOURCE_CONNECT_URL_POST,
    ),
    WebDevResource("db/setDatasourceEnabled", "db/setDatasourceEnabled", SET_DATASOURCE_ENABLED_POST),
    WebDevResource(
        "db/setDatasourceMaxConnections",
        "db/setDatasourceMaxConnections",
        SET_DATASOURCE_MAX_CONNECTIONS_POST,
    ),
    WebDevResource("db/removeDatasource", "db/removeDatasource", REMOVE_DATASOURCE_POST),
    WebDevResource("db/beginTransaction", "db/beginTransaction", BEGIN_TRANSACTION_POST),
    WebDevResource("db/commitTransaction", "db/commitTransaction", COMMIT_TRANSACTION_POST),
    WebDevResource("db/rollbackTransaction", "db/rollbackTransaction", ROLLBACK_TRANSACTION_POST),
    WebDevResource("db/closeTransaction", "db/closeTransaction", CLOSE_TRANSACTION_POST),
    WebDevResource("db/runQuery", "db/runQuery", RUN_QUERY_POST),
    WebDevResource("db/runScalarQuery", "db/runScalarQuery", RUN_SCALAR_QUERY_POST),
    WebDevResource("db/runScalarPrepQuery", "db/runScalarPrepQuery", RUN_SCALAR_PREP_QUERY_POST),
    WebDevResource("db/runPrepQuery", "db/runPrepQuery", RUN_PREP_QUERY_POST),
    WebDevResource("db/runPrepUpdate", "db/runPrepUpdate", RUN_PREP_UPDATE_POST),
    WebDevResource("db/runUpdateQuery", "db/runUpdateQuery", RUN_UPDATE_QUERY_POST),
    WebDevResource("db/runNamedQuery", "db/runNamedQuery", RUN_NAMED_QUERY_POST),
]
