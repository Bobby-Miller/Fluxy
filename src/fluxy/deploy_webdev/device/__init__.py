from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


LIST_DEVICES_POST = COMMON + r'''


def _dataset_rows(dataset):
    rows = []
    column_names = list(dataset.getColumnNames())
    for row_index in range(dataset.getRowCount()):
        item = {}
        for column_name in column_names:
            value = dataset.getValueAt(row_index, column_name)
            if value is not None:
                item[str(column_name)] = value if isinstance(value, bool) else str(value)
        if "name" not in item and "Name" in item:
            item["name"] = item["Name"]
        if "enabled" not in item and "Enabled" in item:
            item["enabled"] = bool(item["Enabled"])
        if "state" not in item and "State" in item:
            item["state"] = item["State"]
        if "driver" not in item and "Driver" in item:
            item["driver"] = item["Driver"]
        rows.append(item)
    return rows


def doPost(request, session):
    operation = "Device.listDevices"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        devices = _dataset_rows(system.device.listDevices())
        _log_success(operation)
        return {"json": {"ok": True, "devices": devices}}
    except Exception, exc:
        _log_error(operation, "listDevices failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


ADD_DEVICE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Device.addDevice"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        device_type = payload.get("deviceType") or payload.get("device_type")
        device_name = payload.get("deviceName") or payload.get("device_name")
        device_props = payload.get("deviceProps") or payload.get("device_props") or {}
        description = payload.get("description")
        if not isinstance(device_type, basestring):
            return _bad_request("Request must include deviceType string", _request_debug(request))
        if not isinstance(device_name, basestring):
            return _bad_request("Request must include deviceName string", _request_debug(request))
        if not isinstance(device_props, dict):
            return _bad_request("deviceProps must be an object", _request_debug(request))
        if description is None:
            system.device.addDevice(deviceType=device_type, deviceName=device_name, deviceProps=device_props)
        else:
            system.device.addDevice(deviceType=device_type, deviceName=device_name, deviceProps=device_props, description=str(description))
        _log_success(operation)
        return {"json": {"ok": True, "deviceName": device_name}}
    except Exception, exc:
        _log_error(operation, "addDevice failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


REMOVE_DEVICE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Device.removeDevice"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        device_name = payload.get("deviceName") or payload.get("device_name")
        if not isinstance(device_name, basestring):
            return _bad_request("Request must include deviceName string", _request_debug(request))
        system.device.removeDevice(device_name)
        _log_success(operation)
        return {"json": {"ok": True, "deviceName": device_name}}
    except Exception, exc:
        _log_error(operation, "removeDevice failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


SET_DEVICE_ENABLED_POST = COMMON + r'''


def doPost(request, session):
    operation = "Device.setDeviceEnabled"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        device_name = payload.get("deviceName") or payload.get("device_name")
        enabled = payload.get("enabled")
        if not isinstance(device_name, basestring):
            return _bad_request("Request must include deviceName string", _request_debug(request))
        if not isinstance(enabled, bool):
            return _bad_request("Request must include enabled boolean", _request_debug(request))
        system.device.setDeviceEnabled(device_name, enabled)
        _log_success(operation)
        return {"json": {"ok": True, "deviceName": device_name, "enabled": enabled}}
    except Exception, exc:
        _log_error(operation, "setDeviceEnabled failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


RESOURCES = [
    WebDevResource("device/listDevices", "listDevices", LIST_DEVICES_POST),
    WebDevResource("device/addDevice", "addDevice", ADD_DEVICE_POST),
    WebDevResource("device/removeDevice", "removeDevice", REMOVE_DEVICE_POST),
    WebDevResource("device/setDeviceEnabled", "setDeviceEnabled", SET_DEVICE_ENABLED_POST),
]
