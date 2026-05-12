# Ignition WebDev Python Resource
# Suggested resource path: /system/webdev/Fluxy/writeBlocking
#
# This runs inside Ignition and adapts an HTTP request to system.tag.writeBlocking.


AUTH_TOKEN = ""  # Optional shared secret. Leave blank to disable bearer-token auth.
DEFAULT_TIMEOUT_MS = 45000


def _unauthorized():
    return {"json": {"ok": False, "error": "Unauthorized"}, "status": 401}


def _bad_request(message):
    return {"json": {"ok": False, "error": message}, "status": 400}


def _auth_ok(request):
    if not AUTH_TOKEN:
        return True
    headers = request.get("headers", {}) or {}
    authorization = headers.get("Authorization") or headers.get("authorization") or ""
    return authorization == "Bearer %s" % AUTH_TOKEN


def _json_body(request):
    data = request.get("data") or request.get("body") or "{}"
    if hasattr(data, "tostring"):
        data = data.tostring()
    return system.util.jsonDecode(str(data))


def doPost(request, session):
    if not _auth_ok(request):
        return _unauthorized()

    try:
        payload = _json_body(request)
        tag_paths = payload.get("tagPaths") or payload.get("tag_paths")
        values = payload.get("values")
        timeout_ms = int(payload.get("timeoutMs") or payload.get("timeout_ms") or DEFAULT_TIMEOUT_MS)
        if not isinstance(tag_paths, list):
            return _bad_request("Request must include tagPaths list")
        if not isinstance(values, list):
            return _bad_request("Request must include values list")
        if len(tag_paths) != len(values):
            return _bad_request("tagPaths and values must have the same length")

        quality_codes = system.tag.writeBlocking(tag_paths, values, timeout_ms)
        qualities = []
        for index in range(len(tag_paths)):
            qualities.append({
                "tagPath": tag_paths[index],
                "quality": str(quality_codes[index]),
            })

        return {"json": {"ok": True, "qualities": qualities}}
    except Exception, exc:
        system.util.getLogger("Fluxy.WebDev.Write").error("writeBlocking failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
