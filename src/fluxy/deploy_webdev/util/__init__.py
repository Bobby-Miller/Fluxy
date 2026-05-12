from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


DATASET_HELPERS = r'''


def _dataset_to_wire(dataset):
    rows = []
    column_names = list(dataset.getColumnNames())
    for row_index in range(dataset.getRowCount()):
        row = []
        for column_name in column_names:
            value = dataset.getValueAt(row_index, column_name)
            if hasattr(value, "getTime"):
                value = value.getTime()
            elif value is not None and not isinstance(value, (basestring, int, long, float, bool)):
                value = str(value)
            row.append(value)
        rows.append(row)
    return {"rows": rows, "columns": column_names}
'''


GET_VERSION_POST = COMMON + r'''


def doPost(request, session):
    operation = "Util.getVersion"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        version = system.util.getVersion()
        _log_success(operation)
        return {"json": {"ok": True, "version": str(version), "major": version.major, "minor": version.minor}}
    except Exception, exc:
        _log_error(operation, "getVersion failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


GET_MODULES_POST = COMMON + DATASET_HELPERS + r'''


def doPost(request, session):
    operation = "Util.getModules"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        result = _dataset_to_wire(system.util.getModules())
        _log_success(operation)
        return {"json": {"ok": True, "result": result, "resultSource": "ignition.dataset", "resultMessage": "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings"}}
    except Exception, exc:
        _log_error(operation, "getModules failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


GET_GATEWAY_STATUS_POST = COMMON + r'''


def doPost(request, session):
    operation = "Util.getGatewayStatus"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        gateway_address = payload.get("gatewayAddress") or payload.get("gateway_address")
        connect_timeout = payload.get("connectTimeoutMillis") or payload.get("connect_timeout_millis")
        socket_timeout = payload.get("socketTimeoutMillis") or payload.get("socket_timeout_millis")
        bypass_cert_validation = payload.get("bypassCertValidation")
        if not isinstance(gateway_address, basestring):
            return _bad_request("Request must include gatewayAddress string", _request_debug(request))
        if connect_timeout is None and socket_timeout is None and bypass_cert_validation is None:
            status = system.util.getGatewayStatus(gateway_address)
        elif bypass_cert_validation is None:
            status = system.util.getGatewayStatus(gateway_address, int(connect_timeout or 5000), int(socket_timeout or 5000))
        else:
            status = system.util.getGatewayStatus(gateway_address, int(connect_timeout or 5000), int(socket_timeout or 5000), bool(bypass_cert_validation))
        _log_success(operation)
        return {"json": {"ok": True, "status": str(status)}}
    except Exception, exc:
        _log_error(operation, "getGatewayStatus failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


GET_PROJECT_NAME_POST = COMMON + r'''


def doPost(request, session):
    operation = "Util.getProjectName"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        project_name = system.util.getProjectName()
        _log_success(operation)
        return {"json": {"ok": True, "projectName": project_name}}
    except Exception, exc:
        _log_error(operation, "getProjectName failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


AUDIT_POST = COMMON + r'''


def doPost(request, session):
    operation = "Util.audit"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        action = payload.get("action")
        if not isinstance(action, basestring):
            return _bad_request("Request must include action string", _request_debug(request))
        event_timestamp = payload.get("eventTimestamp") or payload.get("event_timestamp")
        if event_timestamp is not None:
            event_timestamp = system.date.fromMillis(long(event_timestamp))
        kwargs = {"action": action}
        optional = {
            "actionTarget": payload.get("actionTarget") or payload.get("action_target"),
            "actionValue": payload.get("actionValue") or payload.get("action_value"),
            "auditProfile": payload.get("auditProfile") or payload.get("audit_profile"),
            "actor": payload.get("actor"),
            "actorHost": payload.get("actorHost") or payload.get("actor_host"),
            "originatingSystem": payload.get("originatingSystem") or payload.get("originating_system"),
            "eventTimestamp": event_timestamp,
            "originatingContext": payload.get("originatingContext") or payload.get("originating_context"),
            "statusCode": payload.get("statusCode") or payload.get("status_code"),
        }
        for key, value in optional.items():
            if value is not None:
                kwargs[key] = value
        system.util.audit(**kwargs)
        _log_success(operation)
        return {"json": {"ok": True}}
    except Exception, exc:
        _log_error(operation, "audit failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


QUERY_AUDIT_LOG_POST = COMMON + DATASET_HELPERS + r'''


def doPost(request, session):
    operation = "Util.queryAuditLog"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        audit_profile_name = payload.get("auditProfileName") or payload.get("audit_profile_name")
        if not isinstance(audit_profile_name, basestring):
            return _bad_request("Request must include auditProfileName string", _request_debug(request))
        start_date = payload.get("startDate") or payload.get("start_date")
        end_date = payload.get("endDate") or payload.get("end_date")
        if start_date is not None:
            start_date = system.date.fromMillis(long(start_date))
        if end_date is not None:
            end_date = system.date.fromMillis(long(end_date))
        result = system.util.queryAuditLog(
            audit_profile_name,
            start_date,
            end_date,
            payload.get("actorFilter") or payload.get("actor_filter"),
            payload.get("actionFilter") or payload.get("action_filter"),
            payload.get("targetFilter") or payload.get("target_filter"),
            payload.get("valueFilter") or payload.get("value_filter"),
            payload.get("systemFilter") or payload.get("system_filter"),
            payload.get("contextFilter") or payload.get("context_filter"),
        )
        _log_success(operation)
        return {"json": {"ok": True, "result": _dataset_to_wire(result), "resultSource": "ignition.dataset", "resultMessage": "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings"}}
    except Exception, exc:
        _log_error(operation, "queryAuditLog failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


RESOURCES = [
    WebDevResource("util/getVersion", "getVersion", GET_VERSION_POST),
    WebDevResource("util/getModules", "getModules", GET_MODULES_POST),
    WebDevResource("util/getGatewayStatus", "getGatewayStatus", GET_GATEWAY_STATUS_POST),
    WebDevResource("util/getProjectName", "getProjectName", GET_PROJECT_NAME_POST),
    WebDevResource("util/audit", "audit", AUDIT_POST),
    WebDevResource("util/queryAuditLog", "queryAuditLog", QUERY_AUDIT_LOG_POST),
]
