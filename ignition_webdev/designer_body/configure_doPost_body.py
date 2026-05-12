AUTH_TOKEN = ""  # Optional bearer token. Leave blank to disable auth.
DEFAULT_COLLISION_POLICY = "o"


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


if not _auth_ok(request):
    return _unauthorized()

try:
    payload = _json_body(request)
    operation = payload.get("operation")
    if operation == "browse":
        path = payload.get("path") or payload.get("basePath") or payload.get("base_path")
        browse_filter = payload.get("filter") or {}
        if not isinstance(path, basestring):
            return _bad_request("Request must include path string", _request_debug(request))
        if not isinstance(browse_filter, dict):
            return _bad_request("filter must be an object", _request_debug(request))

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

        browse_results = system.tag.browse(path, browse_filter)
        results = [_as_dict(result) for result in browse_results.getResults()]
        return {"json": {"ok": True, "results": results}}

    base_path = payload.get("basePath") or payload.get("base_path")
    tags = payload.get("tags")
    collision_policy = payload.get("collisionPolicy") or payload.get("collision_policy") or DEFAULT_COLLISION_POLICY
    if not isinstance(base_path, basestring):
        return _bad_request("Request must include basePath string", _request_debug(request))
    if not isinstance(tags, list):
        return _bad_request("Request must include tags list", _request_debug(request))

    quality_codes = system.tag.configure(base_path, tags, collision_policy)
    qualities = []
    for index in range(len(quality_codes)):
        name = None
        if index < len(tags) and isinstance(tags[index], dict):
            name = tags[index].get("name")
        qualities.append({"name": name, "quality": str(quality_codes[index])})

    return {"json": {"ok": True, "qualities": qualities}}
except Exception, exc:
    system.util.getLogger("Fluxy.WebDev.Configure").error("configure failed", exc)
    return {"json": {"ok": False, "error": str(exc)}, "status": 500}
