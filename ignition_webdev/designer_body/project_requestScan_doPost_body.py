AUTH_TOKEN = ""  # Optional bearer token. Leave blank to disable auth.


def _unauthorized():
    return {"json": {"ok": False, "error": "Unauthorized"}, "status": 401}


def _auth_ok(request):
    if not AUTH_TOKEN:
        return True
    headers = request.get("headers", {}) or {}
    authorization = headers.get("Authorization") or headers.get("authorization") or ""
    return authorization == "Bearer %s" % AUTH_TOKEN


if not _auth_ok(request):
    return _unauthorized()

try:
    system.project.requestScan()
    return {"json": {"ok": True, "message": "Project scan requested"}}
except Exception, exc:
    system.util.getLogger("Fluxy.WebDev.Project").error("requestScan failed", exc)
    return {"json": {"ok": False, "error": str(exc)}, "status": 500}
