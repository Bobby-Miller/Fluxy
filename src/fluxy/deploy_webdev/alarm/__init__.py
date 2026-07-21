from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


DATASET_HELPERS = r"""


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
"""


QUERY_STATUS_POST = (
    COMMON
    + DATASET_HELPERS
    + r"""


def doPost(request, session):
    operation = "Alarm.queryStatus"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        results = system.alarm.queryStatus(
            priority=payload.get("priority"),
            state=payload.get("state"),
            source=payload.get("source"),
            includeShelved=bool(payload.get("includeShelved", False)),
            provider=payload.get("provider"),
        )
        dataset = results.getDataset()
        _log_success(operation)
        return {"json": {"ok": True, "result": _dataset_to_wire(dataset), "resultSource": "ignition.dataset", "resultMessage": "AlarmQueryResult dataset serialized as columns/rows; Fluxy converted to row mappings"}}
    except Exception, exc:
        _log_error(operation, "queryStatus failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


SHELVE_POST = (
    COMMON
    + r"""


def doPost(request, session):
    operation = "Alarm.shelve"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        paths = payload.get("paths") or payload.get("path")
        if not isinstance(paths, list):
            return _bad_request("Request must include paths list", _request_debug(request))
        timeout_seconds = payload.get("timeoutSeconds") or payload.get("timeout_seconds")
        timeout_minutes = payload.get("timeoutMinutes") or payload.get("timeout_minutes")
        if timeout_seconds is not None:
            system.alarm.shelve(paths, timeoutSeconds=int(timeout_seconds))
        elif timeout_minutes is not None:
            system.alarm.shelve(paths, timeoutMinutes=int(timeout_minutes))
        else:
            system.alarm.shelve(paths)
        _log_success(operation)
        return {"json": {"ok": True}}
    except Exception, exc:
        _log_error(operation, "shelve failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


UNSHELVE_POST = (
    COMMON
    + r"""


def doPost(request, session):
    operation = "Alarm.unshelve"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        paths = payload.get("paths") or payload.get("path")
        if not isinstance(paths, list):
            return _bad_request("Request must include paths list", _request_debug(request))
        system.alarm.unshelve(paths)
        _log_success(operation)
        return {"json": {"ok": True}}
    except Exception, exc:
        _log_error(operation, "unshelve failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


GET_SHELVED_PATHS_POST = (
    COMMON
    + r"""


def doPost(request, session):
    operation = "Alarm.getShelvedPaths"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        rows = []
        for path in system.alarm.getShelvedPaths():
            item = {"raw": str(path)}
            for name, method_name in [("path", "getPath"), ("user", "getUser"), ("expiration", "getExpiration")]:
                try:
                    value = getattr(path, method_name)()
                    if hasattr(value, "getTime"):
                        value = value.getTime()
                    item[name] = str(value) if value is not None else None
                except Exception:
                    pass
            try:
                item["expired"] = bool(path.isExpired())
            except Exception:
                pass
            rows.append(item)
        _log_success(operation)
        return {"json": {"ok": True, "results": rows}}
    except Exception, exc:
        _log_error(operation, "getShelvedPaths failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


ACKNOWLEDGE_POST = (
    COMMON
    + r"""


def doPost(request, session):
    operation = "Alarm.acknowledge"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        alarm_ids = payload.get("alarmIds") or payload.get("alarm_ids")
        notes = payload.get("notes")
        username = payload.get("username") or "fluxy"
        if not isinstance(alarm_ids, list):
            return _bad_request("Request must include alarmIds list", _request_debug(request))
        failed = system.alarm.acknowledge(alarm_ids, notes, username)
        _log_success(operation)
        return {"json": {"ok": True, "failed": [str(alarm_id) for alarm_id in failed]}}
    except Exception, exc:
        _log_error(operation, "acknowledge failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


RESOURCES = [
    WebDevResource("alarm/queryStatus", "queryStatus", QUERY_STATUS_POST),
    WebDevResource("alarm/shelve", "shelve", SHELVE_POST),
    WebDevResource("alarm/unshelve", "unshelve", UNSHELVE_POST),
    WebDevResource("alarm/getShelvedPaths", "getShelvedPaths", GET_SHELVED_PATHS_POST),
    WebDevResource("alarm/acknowledge", "acknowledge", ACKNOWLEDGE_POST),
]
