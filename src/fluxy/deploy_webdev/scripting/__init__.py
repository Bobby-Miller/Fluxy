from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


RUN_FUNCTION_FILE_POST = (
    COMMON
    + r"""

PROJECT_PATH = "__PROJECT_PATH__"
FUNCTION_ROOT = "ignition/script-python/fluxy_functions"


def _safe_function_stem(file_name):
    if not isinstance(file_name, basestring):
        raise ValueError("fileName must be a string")
    if file_name.endswith(".py"):
        file_name = file_name[:-3]
    if not file_name.replace("_", "a").isalnum() or file_name[0].isdigit():
        raise ValueError("fileName must be a Python identifier with optional .py suffix")
    return file_name


def _safe_target_directory(target_directory):
    if target_directory is None or str(target_directory).strip() in ["", "."]:
        return ""
    if not isinstance(target_directory, basestring):
        raise ValueError("targetDirectory must be a string")
    parts = target_directory.replace("\\", "/").split("/")
    safe_parts = []
    for part in parts:
        if not part or part == ".." or part[0].isdigit() or not part.replace("_", "a").isalnum():
            raise ValueError("targetDirectory must contain only Python identifier path segments")
        safe_parts.append(part)
    return "/".join(safe_parts)


def doPost(request, session):
    operation = "Scripting.runFunctionFile"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        file_name = payload.get("fileName") or payload.get("file_name")
        target_directory = payload.get("targetDirectory") or payload.get("target_directory")
        args = payload.get("args") or []
        kwargs = payload.get("kwargs") or {}
        if not isinstance(args, list):
            return _bad_request("args must be a list", _request_debug(request))
        if not isinstance(kwargs, dict):
            return _bad_request("kwargs must be an object", _request_debug(request))

        stem = _safe_function_stem(file_name)
        target_directory = _safe_target_directory(target_directory)
        if target_directory:
            code_path = PROJECT_PATH + "/" + FUNCTION_ROOT + "/" + target_directory + "/" + stem + "/code.py"
        else:
            code_path = PROJECT_PATH + "/" + FUNCTION_ROOT + "/" + stem + "/code.py"
        source_file = open(code_path, "r")
        try:
            source = source_file.read()
        finally:
            source_file.close()

        namespace = {"system": system}
        exec source in namespace
        function = namespace.get(stem)
        if function is None or not callable(function):
            raise ValueError("Function %s was not defined in %s" % (stem, code_path))

        result = function(*args, **kwargs)
        _log_success(operation)
        return {"json": {"ok": True, "result": result}}
    except Exception, exc:
        _log_error(operation, "runFunctionFile failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)

RESOURCES = [
    WebDevResource(
        "scripting/runFunctionFile", "scripting/runFunctionFile", RUN_FUNCTION_FILE_POST
    ),
]
