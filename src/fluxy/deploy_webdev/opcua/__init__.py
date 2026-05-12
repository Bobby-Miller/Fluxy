from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


ADD_CONNECTION_POST = COMMON + r'''


def doPost(request, session):
    operation = "OpcUa.addConnection"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        name = payload.get("name")
        description = payload.get("description") or ""
        discovery_url = payload.get("discoveryUrl") or payload.get("discovery_url")
        endpoint_url = payload.get("endpointUrl") or payload.get("endpoint_url")
        security_policy = payload.get("securityPolicy") or payload.get("security_policy") or "None"
        security_mode = payload.get("securityMode") or payload.get("security_mode") or "None"
        settings = payload.get("settings") or {}
        if not isinstance(name, basestring):
            return _bad_request("Request must include name string", _request_debug(request))
        if not isinstance(discovery_url, basestring):
            return _bad_request("Request must include discoveryUrl string", _request_debug(request))
        if not isinstance(endpoint_url, basestring):
            return _bad_request("Request must include endpointUrl string", _request_debug(request))
        if not isinstance(settings, dict):
            return _bad_request("settings must be an object", _request_debug(request))
        system.opcua.addConnection(
            str(name),
            str(description),
            str(discovery_url),
            str(endpoint_url),
            str(security_policy),
            str(security_mode),
            settings,
        )
        _log_success(operation)
        return {"json": {"ok": True, "name": name}}
    except Exception, exc:
        _log_error(operation, "addConnection failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


REMOVE_CONNECTION_POST = COMMON + r'''


def doPost(request, session):
    operation = "OpcUa.removeConnection"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        name = payload.get("name")
        if not isinstance(name, basestring):
            return _bad_request("Request must include name string", _request_debug(request))
        system.opcua.removeConnection(str(name))
        _log_success(operation)
        return {"json": {"ok": True, "name": name}}
    except Exception, exc:
        _log_error(operation, "removeConnection failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


RESOURCES = [
    WebDevResource("opcua/addConnection", "addConnection", ADD_CONNECTION_POST),
    WebDevResource("opcua/removeConnection", "removeConnection", REMOVE_CONNECTION_POST),
]
