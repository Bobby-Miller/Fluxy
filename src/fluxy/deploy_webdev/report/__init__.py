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


GET_REPORT_NAMES_AS_LIST_POST = COMMON + r'''


def doPost(request, session):
    operation = "Report.getReportNamesAsList"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        project = payload.get("project")
        if not isinstance(project, basestring):
            return _bad_request("Request must include project string", _request_debug(request))
        reports = [str(report) for report in system.report.getReportNamesAsList(project)]
        _log_success(operation)
        return {"json": {"ok": True, "reports": reports}}
    except Exception, exc:
        _log_error(operation, "getReportNamesAsList failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


GET_REPORT_NAMES_AS_DATASET_POST = COMMON + DATASET_HELPERS + r'''


def doPost(request, session):
    operation = "Report.getReportNamesAsDataset"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        project = payload.get("project")
        include_report_name = payload.get("includeReportName")
        if include_report_name is None:
            include_report_name = payload.get("include_report_name")
        if include_report_name is None:
            include_report_name = True
        if not isinstance(project, basestring):
            return _bad_request("Request must include project string", _request_debug(request))
        result = system.report.getReportNamesAsDataset(project, bool(include_report_name))
        _log_success(operation)
        return {"json": {"ok": True, "result": _dataset_to_wire(result), "resultSource": "ignition.dataset", "resultMessage": "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings"}}
    except Exception, exc:
        _log_error(operation, "getReportNamesAsDataset failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


EXECUTE_REPORT_POST = COMMON + r'''

import base64


def _bytes_to_base64(values):
    raw = "".join(chr((int(value) + 256) % 256) for value in values)
    return base64.b64encode(raw)


def doPost(request, session):
    operation = "Report.executeReport"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        path = payload.get("path")
        project = payload.get("project")
        parameters = payload.get("parameters") or {}
        file_type = payload.get("fileType") or payload.get("file_type") or "pdf"
        if not isinstance(path, basestring):
            return _bad_request("Request must include path string", _request_debug(request))
        if not isinstance(project, basestring):
            return _bad_request("Request must include project string", _request_debug(request))
        if not isinstance(parameters, dict):
            return _bad_request("parameters must be an object", _request_debug(request))
        result = system.report.executeReport(path=path, project=project, parameters=parameters, fileType=file_type)
        _log_success(operation)
        return {"json": {"ok": True, "contentBase64": _bytes_to_base64(result), "fileType": str(file_type), "size": len(result)}}
    except Exception, exc:
        _log_error(operation, "executeReport failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


RESOURCES = [
    WebDevResource("report/getReportNamesAsList", "getReportNamesAsList", GET_REPORT_NAMES_AS_LIST_POST),
    WebDevResource("report/getReportNamesAsDataset", "getReportNamesAsDataset", GET_REPORT_NAMES_AS_DATASET_POST),
    WebDevResource("report/executeReport", "executeReport", EXECUTE_REPORT_POST),
]
