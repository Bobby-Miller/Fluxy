from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


REQUEST_SCAN_POST = COMMON + r'''


def doPost(request, session):
    operation = "Project.requestScan"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        system.project.requestScan()
        _log_success(operation)
        return {"json": {"ok": True, "message": "Project scan requested"}}
    except Exception, exc:
        _log_error(operation, "requestScan failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

GET_PROJECT_NAME_POST = COMMON + r'''


def doPost(request, session):
    operation = "Project.getProjectName"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        project_name = system.project.getProjectName()
        _log_success(operation)
        return {"json": {"ok": True, "projectName": project_name}}
    except Exception, exc:
        _log_error(operation, "getProjectName failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

GET_PROJECT_NAMES_POST = COMMON + r'''


def doPost(request, session):
    operation = "Project.getProjectNames"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        project_names = [str(project_name) for project_name in system.project.getProjectNames()]
        _log_success(operation)
        return {"json": {"ok": True, "projectNames": project_names}}
    except Exception, exc:
        _log_error(operation, "getProjectNames failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RESOURCES = [
    WebDevResource("project/requestScan", "project/requestScan", REQUEST_SCAN_POST),
    WebDevResource("project/getProjectName", "project/getProjectName", GET_PROJECT_NAME_POST),
    WebDevResource("project/getProjectNames", "project/getProjectNames", GET_PROJECT_NAMES_POST),
]
