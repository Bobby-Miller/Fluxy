from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


VALUE_HELPERS = r'''


def _qualified_value(value):
    timestamp = value.getTimestamp()
    return {
        "value": value.getValue(),
        "quality": str(value.getQuality()),
        "timestamp": timestamp.getTime() if timestamp is not None else None,
    }


def _browse_tag(tag):
    item = {"raw": str(tag)}
    for key, method_name in [
        ("opcServer", "getOpcServer"),
        ("opcItemPath", "getOpcItemPath"),
        ("type", "getType"),
        ("displayName", "getDisplayName"),
        ("displayPath", "getDisplayPath"),
        ("dataType", "getDataType"),
    ]:
        try:
            value = getattr(tag, method_name)()
            item[key] = str(value) if value is not None else None
        except Exception:
            pass
    return item


def _browse_element(element):
    item = {"raw": str(element)}
    for key, method_name in [
        ("displayName", "getDisplayName"),
        ("elementType", "getElementType"),
        ("nodeId", "getNodeId"),
        ("serverName", "getServerName"),
        ("dataType", "getDataType"),
        ("datatype", "getDatatype"),
        ("description", "getDescription"),
    ]:
        try:
            value = getattr(element, method_name)()
            item[key] = str(value) if value is not None else None
        except Exception:
            pass
    return item
'''


GET_SERVERS_POST = COMMON + r'''


def doPost(request, session):
    operation = "Opc.getServers"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        servers = system.opc.getServers(bool(payload.get("includeDisabled", False)))
        _log_success(operation)
        return {"json": {"ok": True, "servers": [str(server) for server in servers]}}
    except Exception, exc:
        _log_error(operation, "getServers failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


GET_SERVER_STATE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Opc.getServerState"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        opc_server = payload.get("opcServer") or payload.get("opc_server")
        if not isinstance(opc_server, basestring):
            return _bad_request("Request must include opcServer string", _request_debug(request))
        state = system.opc.getServerState(opc_server)
        _log_success(operation)
        return {"json": {"ok": True, "state": str(state) if state is not None else None}}
    except Exception, exc:
        _log_error(operation, "getServerState failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


BROWSE_POST = COMMON + VALUE_HELPERS + r'''


def doPost(request, session):
    operation = "Opc.browse"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        results = system.opc.browse(
            opcServer=payload.get("opcServer") or payload.get("opc_server"),
            device=payload.get("device"),
            folderPath=payload.get("folderPath") or payload.get("folder_path"),
            opcItemPath=payload.get("opcItemPath") or payload.get("opc_item_path"),
        )
        _log_success(operation)
        return {"json": {"ok": True, "results": [_browse_tag(tag) for tag in results]}}
    except Exception, exc:
        _log_error(operation, "browse failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


BROWSE_SERVER_POST = COMMON + VALUE_HELPERS + r'''


def doPost(request, session):
    operation = "Opc.browseServer"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        opc_server = payload.get("opcServer") or payload.get("opc_server")
        node_id = payload.get("nodeId") or payload.get("node_id")
        if not isinstance(opc_server, basestring):
            return _bad_request("Request must include opcServer string", _request_debug(request))
        if not isinstance(node_id, basestring):
            return _bad_request("Request must include nodeId string", _request_debug(request))
        results = system.opc.browseServer(opc_server, node_id)
        _log_success(operation)
        return {"json": {"ok": True, "results": [_browse_element(element) for element in results]}}
    except Exception, exc:
        _log_error(operation, "browseServer failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


BROWSE_SIMPLE_POST = COMMON + VALUE_HELPERS + r'''


def doPost(request, session):
    operation = "Opc.browseSimple"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        results = system.opc.browseSimple(
            payload.get("opcServer") or payload.get("opc_server"),
            payload.get("device"),
            payload.get("folderPath") or payload.get("folder_path"),
            payload.get("opcItemPath") or payload.get("opc_item_path"),
        )
        _log_success(operation)
        return {"json": {"ok": True, "results": [_browse_tag(tag) for tag in results]}}
    except Exception, exc:
        _log_error(operation, "browseSimple failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


READ_VALUE_POST = COMMON + VALUE_HELPERS + r'''


def doPost(request, session):
    operation = "Opc.readValue"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        opc_server = payload.get("opcServer") or payload.get("opc_server")
        item_path = payload.get("itemPath") or payload.get("item_path")
        if not isinstance(opc_server, basestring):
            return _bad_request("Request must include opcServer string", _request_debug(request))
        if not isinstance(item_path, basestring):
            return _bad_request("Request must include itemPath string", _request_debug(request))
        value = _qualified_value(system.opc.readValue(opc_server, item_path))
        _log_success(operation)
        value["ok"] = True
        return {"json": value}
    except Exception, exc:
        _log_error(operation, "readValue failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


READ_VALUES_POST = COMMON + VALUE_HELPERS + r'''


def doPost(request, session):
    operation = "Opc.readValues"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        opc_server = payload.get("opcServer") or payload.get("opc_server")
        item_paths = payload.get("itemPaths") or payload.get("item_paths")
        if not isinstance(opc_server, basestring):
            return _bad_request("Request must include opcServer string", _request_debug(request))
        if not isinstance(item_paths, list):
            return _bad_request("Request must include itemPaths list", _request_debug(request))
        values = [_qualified_value(value) for value in system.opc.readValues(opc_server, item_paths)]
        _log_success(operation)
        return {"json": {"ok": True, "values": values}}
    except Exception, exc:
        _log_error(operation, "readValues failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


WRITE_VALUE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Opc.writeValue"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        quality = system.opc.writeValue(
            payload.get("opcServer") or payload.get("opc_server"),
            payload.get("itemPath") or payload.get("item_path"),
            payload.get("value"),
        )
        _log_success(operation)
        return {"json": {"ok": True, "quality": str(quality)}}
    except Exception, exc:
        _log_error(operation, "writeValue failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


WRITE_VALUES_POST = COMMON + r'''


def doPost(request, session):
    operation = "Opc.writeValues"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        qualities = system.opc.writeValues(
            payload.get("opcServer") or payload.get("opc_server"),
            payload.get("itemPaths") or payload.get("item_paths"),
            payload.get("values"),
        )
        _log_success(operation)
        return {"json": {"ok": True, "qualities": [str(quality) for quality in qualities]}}
    except Exception, exc:
        _log_error(operation, "writeValues failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


RESOURCES = [
    WebDevResource("opc/getServers", "getServers", GET_SERVERS_POST),
    WebDevResource("opc/getServerState", "getServerState", GET_SERVER_STATE_POST),
    WebDevResource("opc/browse", "browse", BROWSE_POST),
    WebDevResource("opc/browseServer", "browseServer", BROWSE_SERVER_POST),
    WebDevResource("opc/browseSimple", "browseSimple", BROWSE_SIMPLE_POST),
    WebDevResource("opc/readValue", "readValue", READ_VALUE_POST),
    WebDevResource("opc/readValues", "readValues", READ_VALUES_POST),
    WebDevResource("opc/writeValue", "writeValue", WRITE_VALUE_POST),
    WebDevResource("opc/writeValues", "writeValues", WRITE_VALUES_POST),
]
