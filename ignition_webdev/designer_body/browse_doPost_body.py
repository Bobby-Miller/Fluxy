AUTH_TOKEN = ""  # Optional bearer token. Leave blank to disable auth.


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


def _as_dict(result):
    item = {}
    for key in ["name", "fullPath", "tagType", "dataType", "hasChildren"]:
        value = None
        try:
            value = result[key]
        except Exception:
            try:
                value = getattr(result, key)
            except Exception:
                pass
        if value is None:
            continue
        if key == "hasChildren":
            item[key] = bool(value)
        else:
            item[key] = str(value)
    return item


if not _auth_ok(request):
    return _unauthorized()

try:
    payload = _json_body(request)
    path = payload.get("path") or payload.get("basePath") or payload.get("base_path")
    browse_filter = payload.get("filter") or {}
    browse_results = system.tag.browse(path, browse_filter)
    results = [_as_dict(result) for result in browse_results.getResults()]
    return {"json": {"ok": True, "results": results}}
except Exception, exc:
    system.util.getLogger("Fluxy.WebDev.Browse").error("browse failed", exc)
    return {"json": {"ok": False, "error": str(exc)}, "status": 500}
