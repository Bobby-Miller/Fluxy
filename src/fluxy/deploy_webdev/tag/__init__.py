from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


READ_POST = COMMON + r'''


def _value_to_wire(value):
    if value is None or isinstance(value, (basestring, int, long, float, bool)):
        return value
    if hasattr(value, "getTime"):
        return value.getTime()
    try:
        return _value_to_wire(value.toDict())
    except Exception:
        pass
    if isinstance(value, dict):
        return dict((str(key), _value_to_wire(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [_value_to_wire(item) for item in value]
    try:
        return system.util.jsonDecode(system.util.jsonEncode(value))
    except Exception:
        return str(value)


def doPost(request, session):
    operation = "Tag.readBlocking"
    DEFAULT_TIMEOUT_MS = 45000
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
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
                "value": _value_to_wire(qualified_value.value),
                "quality": str(qualified_value.quality),
                "timestamp": system.date.format(qualified_value.timestamp, "yyyy-MM-dd'T'HH:mm:ss.SSSXXX") if qualified_value.timestamp is not None else None,
            })
        _log_success(operation)
        return {"json": {"ok": True, "values": values}}
    except Exception, exc:
        _log_error(operation, "readBlocking failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

WRITE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Tag.writeBlocking"
    DEFAULT_TIMEOUT_MS = 45000
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        tag_paths = payload.get("tagPaths") or payload.get("tag_paths")
        values = payload.get("values")
        timeout_ms = int(payload.get("timeoutMs") or payload.get("timeout_ms") or DEFAULT_TIMEOUT_MS)
        if not isinstance(tag_paths, list):
            return _bad_request("Request must include tagPaths list", _request_debug(request))
        if not isinstance(values, list):
            return _bad_request("Request must include values list", _request_debug(request))
        if len(tag_paths) != len(values):
            return _bad_request("tagPaths and values must have the same length")
        quality_codes = system.tag.writeBlocking(tag_paths, values, timeout_ms)
        qualities = []
        for index in range(len(tag_paths)):
            qualities.append({"tagPath": tag_paths[index], "quality": str(quality_codes[index])})
        _log_success(operation)
        return {"json": {"ok": True, "qualities": qualities}}
    except Exception, exc:
        _log_error(operation, "writeBlocking failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

DELETE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Tag.deleteTags"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        tag_paths = payload.get("tagPaths") or payload.get("tag_paths")
        if not isinstance(tag_paths, list):
            return _bad_request("Request must include tagPaths list", _request_debug(request))
        quality_codes = system.tag.deleteTags(tag_paths)
        qualities = []
        for index in range(len(tag_paths)):
            qualities.append({"tagPath": tag_paths[index], "quality": str(quality_codes[index])})
        _log_success(operation)
        return {"json": {"ok": True, "qualities": qualities}}
    except Exception, exc:
        _log_error(operation, "deleteTags failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

COPY_POST = COMMON + r'''


def doPost(request, session):
    operation = "Tag.copy"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        tag_paths = payload.get("tagPaths") or payload.get("tag_paths")
        destination_path = payload.get("destinationPath") or payload.get("destination_path")
        collision_policy = payload.get("collisionPolicy") or payload.get("collision_policy") or "o"
        if not isinstance(tag_paths, list):
            return _bad_request("Request must include tagPaths list", _request_debug(request))
        if not isinstance(destination_path, basestring):
            return _bad_request("Request must include destinationPath string", _request_debug(request))
        quality_codes = system.tag.copy(tag_paths, destination_path, collision_policy)
        qualities = []
        for index in range(len(tag_paths)):
            qualities.append({
                "tagPath": tag_paths[index],
                "destinationPath": destination_path,
                "quality": str(quality_codes[index]),
            })
        _log_success(operation)
        return {"json": {"ok": True, "qualities": qualities}}
    except Exception, exc:
        _log_error(operation, "copy failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

MOVE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Tag.move"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        source_path = payload.get("sourcePath") or payload.get("source_path")
        destination_path = payload.get("destinationPath") or payload.get("destination_path")
        if not isinstance(source_path, basestring):
            return _bad_request("Request must include sourcePath string", _request_debug(request))
        if not isinstance(destination_path, basestring):
            return _bad_request("Request must include destinationPath string", _request_debug(request))
        quality_codes = system.tag.move([source_path], destination_path, "o")
        _log_success(operation)
        return {"json": {"ok": True, "quality": {"sourcePath": source_path, "destinationPath": destination_path, "quality": str(quality_codes[0])}}}
    except Exception, exc:
        _log_error(operation, "move failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RENAME_POST = COMMON + r'''


def doPost(request, session):
    operation = "Tag.rename"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        tag_path = payload.get("tagPath") or payload.get("tag_path")
        new_name = payload.get("newName") or payload.get("new_name")
        if not isinstance(tag_path, basestring):
            return _bad_request("Request must include tagPath string", _request_debug(request))
        if not isinstance(new_name, basestring):
            return _bad_request("Request must include newName string", _request_debug(request))
        quality_code = system.tag.rename(tag_path, new_name)
        _log_success(operation)
        return {"json": {"ok": True, "quality": {"tagPath": tag_path, "newName": new_name, "quality": str(quality_code)}}}
    except Exception, exc:
        _log_error(operation, "rename failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

IMPORT_POST = COMMON + r'''


def doPost(request, session):
    import os
    import tempfile

    operation = "Tag.importTags"
    if not _auth_ok(request):
        return _unauthorized()
    temp_path = None
    try:
        _log_start(operation)
        payload = _json_body(request)
        tags = payload.get("tags")
        base_path = payload.get("basePath") or payload.get("base_path")
        collision_policy = payload.get("collisionPolicy") or payload.get("collision_policy") or "o"
        if tags is None:
            return _bad_request("Request must include tags", _request_debug(request))
        if not isinstance(base_path, basestring):
            return _bad_request("Request must include basePath string", _request_debug(request))
        if isinstance(tags, basestring):
            raw_json = tags
        else:
            raw_json = system.util.jsonEncode(tags)

        handle, temp_path = tempfile.mkstemp(suffix=".json", prefix="fluxy-import-tags-")
        os.close(handle)
        temp_file = open(temp_path, "w")
        try:
            temp_file.write(raw_json)
        finally:
            temp_file.close()

        quality_codes = system.tag.importTags(temp_path, base_path, collision_policy)
        qualities = []
        for quality_code in quality_codes:
            qualities.append({"quality": str(quality_code)})
        _log_success(operation)
        return {"json": {"ok": True, "qualities": qualities}}
    except Exception, exc:
        _log_error(operation, "importTags failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
    finally:
        if temp_path is not None:
            try:
                os.remove(temp_path)
            except Exception:
                pass
'''

EXPORT_POST = COMMON + r'''


def doPost(request, session):
    import os
    import tempfile

    operation = "Tag.exportTags"
    if not _auth_ok(request):
        return _unauthorized()
    temp_path = None
    try:
        _log_start(operation)
        payload = _json_body(request)
        tag_paths = payload.get("tagPaths") or payload.get("tag_paths")
        recursive = bool(payload.get("recursive", True))
        if not isinstance(tag_paths, list):
            return _bad_request("Request must include tagPaths list", _request_debug(request))

        handle, temp_path = tempfile.mkstemp(suffix=".json", prefix="fluxy-export-tags-")
        os.close(handle)
        system.tag.exportTags(temp_path, tag_paths, recursive)
        try:
            raw_json = system.file.readFileAsString(temp_path)
        except Exception:
            temp_file = open(temp_path, "r")
            try:
                raw_json = temp_file.read()
            finally:
                temp_file.close()
        _log_success(operation)
        return {"json": {"ok": True, "tags": system.util.jsonDecode(raw_json), "rawJson": raw_json}}
    except Exception, exc:
        _log_error(operation, "exportTags failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
    finally:
        if temp_path is not None:
            try:
                os.remove(temp_path)
            except Exception:
                pass
'''

GET_CONFIGURATION_POST = COMMON + r'''


def _value_to_wire(value):
    if value is None or isinstance(value, (basestring, int, long, float, bool)):
        return value
    if hasattr(value, "getTime"):
        return value.getTime()
    try:
        return _value_to_wire(value.toDict())
    except Exception:
        pass
    if isinstance(value, dict):
        return dict((str(key), _value_to_wire(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return [_value_to_wire(item) for item in value]
    try:
        return system.util.jsonDecode(system.util.jsonEncode(value))
    except Exception:
        return str(value)


def _config_value(config, key):
    try:
        value = config[key]
    except Exception:
        try:
            value = getattr(config, key)
        except Exception:
            return None
    if value is None:
        return None
    if key in ["tagType", "dataType", "valueSource"]:
        text = str(value)
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1]
        return text
    return _value_to_wire(value)


def _config_to_dict(config):
    item = {}
    for key in [
        "name",
        "tagType",
        "valueSource",
        "dataType",
        "value",
        "tooltip",
        "documentation",
        "historyEnabled",
        "historyProvider",
        "historySampleMode",
        "historySampleRate",
        "historySampleRateUnits",
        "historyMinTimeBetweenSamples",
        "historyMinTimeUnits",
        "historicalDeadband",
        "historicalDeadbandMode",
        "historyMaxAge",
        "historyMaxAgeUnits",
    ]:
        value = _config_value(config, key)
        if value is not None:
            item[key] = value
    child_tags = _config_value(config, "tags")
    if child_tags is not None:
        item["tags"] = [_config_to_dict(child) for child in child_tags]
    return item


def doPost(request, session):
    operation = "Tag.getConfiguration"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        path = payload.get("path") or payload.get("tagPath") or payload.get("tag_path")
        paths = payload.get("paths") or payload.get("tagPaths") or payload.get("tag_paths")
        recursive = bool(payload.get("recursive", False))
        if paths is not None:
            if not isinstance(paths, list):
                return _bad_request("paths must be a list", _request_debug(request))
            decoded_configs = []
            for current_path in paths:
                if not isinstance(current_path, basestring):
                    return _bad_request("paths must contain path strings", _request_debug(request))
                for config in system.tag.getConfiguration(current_path, recursive):
                    decoded_config = _config_to_dict(config)
                    if "fullPath" not in decoded_config:
                        decoded_config["fullPath"] = current_path
                    decoded_configs.append(decoded_config)
        else:
            if not isinstance(path, basestring):
                return _bad_request("Request must include path string", _request_debug(request))
            configs = system.tag.getConfiguration(path, recursive)
            decoded_configs = [_config_to_dict(config) for config in configs]
        _log_success(operation)
        return {"json": {"ok": True, "configs": decoded_configs}}
    except Exception, exc:
        _log_error(operation, "getConfiguration failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

CONFIGURE_POST = COMMON + r'''


def doPost(request, session):
    operation = "Tag.configure"
    DEFAULT_COLLISION_POLICY = "o"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
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
        _log_success(operation)
        return {"json": {"ok": True, "qualities": qualities}}
    except Exception, exc:
        _log_error(operation, "configure failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

BROWSE_POST = COMMON + r'''


def _browse_result_to_dict(result):
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


def doPost(request, session):
    operation = "Tag.browse"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        path = payload.get("path") or payload.get("basePath") or payload.get("base_path")
        browse_filter = payload.get("filter") or {}
        if not isinstance(path, basestring):
            return _bad_request("Request must include path string", _request_debug(request))
        if not isinstance(browse_filter, dict):
            return _bad_request("filter must be an object", _request_debug(request))
        browse_results = system.tag.browse(path, browse_filter)
        results = [_browse_result_to_dict(result) for result in browse_results.getResults()]
        _log_success(operation)
        return {"json": {"ok": True, "results": results}}
    except Exception, exc:
        _log_error(operation, "browse failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

QUERY_POST = COMMON + r'''


def doPost(request, session):
    operation = "Tag.query"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        provider = payload.get("provider")
        query = payload.get("query") or {}
        limit = payload.get("limit")
        continuation = payload.get("continuation")
        if not isinstance(provider, basestring):
            return _bad_request("Request must include provider string", _request_debug(request))
        if not isinstance(query, dict):
            return _bad_request("query must be an object", _request_debug(request))
        if continuation:
            query_results = system.tag.query(provider, query, int(limit or 0), continuation)
        elif limit is not None:
            query_results = system.tag.query(provider, query, int(limit))
        else:
            query_results = system.tag.query(provider, query)
        results = []
        for result in query_results:
            item = {}
            for key in ["path", "name", "tagType", "dataType", "quality", "valueSource", "value"]:
                value = None
                try:
                    value = result[key]
                except Exception:
                    try:
                        value = getattr(result, key)
                    except Exception:
                        pass
                if value is not None:
                    item[key] = str(value)
            if not item:
                item["raw"] = str(result)
            results.append(item)
        continuation_point = None
        try:
            continuation_point = query_results.continuationPoint
        except Exception:
            try:
                continuation_point = query_results.getContinuationPoint()
            except Exception:
                pass
        _log_success(operation)
        if continuation_point is not None:
            continuation_point = str(continuation_point)
        return {"json": {"ok": True, "results": results, "continuationPoint": continuation_point}}
    except Exception, exc:
        _log_error(operation, "query failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''

RESOURCES = [
    WebDevResource("tag/readBlocking", "readBlocking", READ_POST),
    WebDevResource("tag/writeBlocking", "writeBlocking", WRITE_POST),
    WebDevResource("tag/deleteTags", "deleteTags", DELETE_POST),
    WebDevResource("tag/copy", "copy", COPY_POST),
    WebDevResource("tag/move", "move", MOVE_POST),
    WebDevResource("tag/rename", "rename", RENAME_POST),
    WebDevResource("tag/importTags", "importTags", IMPORT_POST),
    WebDevResource("tag/exportTags", "exportTags", EXPORT_POST),
    WebDevResource("tag/getConfiguration", "getConfiguration", GET_CONFIGURATION_POST),
    WebDevResource("tag/configure", "configure", CONFIGURE_POST),
    WebDevResource("tag/browse", "browse", BROWSE_POST),
    WebDevResource("tag/queryTags", "queryTags", QUERY_POST),
]
