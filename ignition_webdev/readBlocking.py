# Ignition WebDev Python Resource
# Suggested resource path: /system/webdev/Fluxy/readBlocking
#
# This runs inside Ignition and adapts an HTTP request to system.tag.readBlocking.


AUTH_TOKEN = ""  # Optional shared secret. Leave blank to disable bearer-token auth.
DEFAULT_TIMEOUT_MS = 45000


def _unauthorized():
    return {"json": {"ok": False, "error": "Unauthorized"}, "status": 401}


def _bad_request(message, details=None):
    payload = {"ok": False, "error": message}
    if details is not None:
        payload["details"] = details
    return {"json": payload, "status": 400}


def _auth_ok(request):
    if not AUTH_TOKEN:
        return True
    headers = request.get("headers", {}) or {}
    authorization = headers.get("Authorization") or headers.get("authorization") or ""
    return authorization == "Bearer %s" % AUTH_TOKEN


def _json_body(request):
    for key in ["data", "body", "postData", "payload"]:
        data = request.get(key)
        if data is None:
            continue
        if isinstance(data, dict):
            return data
        if hasattr(data, "tostring"):
            data = data.tostring()
        elif hasattr(data, "decode"):
            data = data.decode("utf-8")
        data = str(data).strip()
        if data:
            return system.util.jsonDecode(data)
    return {}


def _request_debug(request):
    details = {"keys": list(request.keys())}
    for key in ["data", "body", "postData", "payload", "params"]:
        if key in request:
            value = request.get(key)
            details[key] = str(type(value))
    return details


def _format_timestamp(timestamp):
    if timestamp is None:
        return None
    return system.date.format(timestamp, "yyyy-MM-dd'T'HH:mm:ss.SSSXXX")


def doPost(request, session):
    if not _auth_ok(request):
        return _unauthorized()

    try:
        payload = _json_body(request)
        tag_paths = payload.get("tagPaths") or payload.get("tag_paths") or payload.get("tag_list")
        timeout_ms = int(payload.get("timeoutMs") or payload.get("timeout_ms") or DEFAULT_TIMEOUT_MS)
        if not isinstance(tag_paths, list):
            return _bad_request("Request must include tagPaths list", _request_debug(request))

        qualified_values = system.tag.readBlocking(tag_paths, timeout_ms)
        values = []
        for index in range(len(tag_paths)):
            qualified_value = qualified_values[index]
            values.append({
                "tagPath": tag_paths[index],
                "value": qualified_value.value,
                "quality": str(qualified_value.quality),
                "timestamp": _format_timestamp(qualified_value.timestamp),
            })

        return {"json": {"ok": True, "values": values}}
    except Exception, exc:
        system.util.getLogger("Fluxy.WebDev.Read").error("readBlocking failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
