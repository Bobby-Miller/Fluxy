# SPDX-FileCopyrightText: 2026 Green Pipe Partners, LLC
# SPDX-License-Identifier: MPL-2.0
# Portions are adapted from Fluxy's MIT-licensed WebDev implementation.
# The preserved MIT notice is in WEBDEV_MIT_NOTICE.

class BadRequest(Exception):
    pass


class Conflict(Exception):
    pass


class HistorianCountLimitExceeded(BadRequest):
    pass


_HISTORY_ROUTE_CACHE = {}
_HISTORY_ROUTE_CACHE_TTL_SECONDS = 60
_HISTORY_ROUTE_CACHE_MAX_PROVIDERS = 128
_HISTORY_PAGE_CACHE = {}
_HISTORY_PAGE_CACHE_ORDER = []
_HISTORY_PAGE_INFLIGHT = {}
_HISTORY_PAGE_CACHE_TTL_SECONDS = 20
_HISTORY_PAGE_CACHE_MAX_WINDOWS = 8
_HISTORY_PAGE_CACHE_MAX_POINTS = 40000
_HISTORY_PAGE_CACHE_MAX_BYTES = 16 * 1024 * 1024
_HISTORY_PAGE_MAX_TOTAL_POINTS = 10000

import threading
_HISTORY_PAGE_CACHE_LOCK = threading.RLock()


def _dataset_to_wire(dataset):
    rows = []
    column_names = list(dataset.getColumnNames())
    for row_index in range(dataset.getRowCount()):
        row = []
        for column_name in column_names:
            value = dataset.getValueAt(row_index, column_name)
            if hasattr(value, "getTime"):
                value = value.getTime()
            elif value is not None and not isinstance(value, (basestring, int, long, float, bool)):
                value = str(value)
            row.append(value)
        rows.append(row)
    return {"columns": column_names, "rows": rows}


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


def _required_list(payload, key):
    value = payload.get(key)
    if not isinstance(value, list):
        raise BadRequest("Request must include %s list" % key)
    return value


def _util_get_version(payload):
    version = system.util.getVersion()
    return {
        "ok": True,
        "version": str(version),
        "major": int(version.major),
        "minor": int(version.minor),
        "transport": "ignition-module",
        "contractVersion": 1,
    }


def _util_query_audit_log(payload):
    profile = payload.get("auditProfileName")
    if not isinstance(profile, basestring):
        raise BadRequest("Request must include auditProfileName string")
    start_date = payload.get("startDate")
    end_date = payload.get("endDate")
    dataset = system.util.queryAuditLog(
        profile,
        system.date.fromMillis(long(start_date)) if start_date is not None else None,
        system.date.fromMillis(long(end_date)) if end_date is not None else None,
        payload.get("actorFilter"),
        payload.get("actionFilter"),
        payload.get("targetFilter"),
        payload.get("valueFilter"),
        payload.get("systemFilter"),
        payload.get("contextFilter"),
    )
    return {
        "ok": True,
        "result": _dataset_to_wire(dataset),
        "resultSource": "ignition.dataset",
    }


def _tag_read_blocking(payload):
    tag_paths = _required_list(payload, "tagPaths")
    timeout_ms = int(payload.get("timeoutMs") or 45000)
    qualified_values = system.tag.readBlocking(tag_paths, timeout_ms)
    values = []
    for index, qualified_value in enumerate(qualified_values):
        values.append({
            "tagPath": tag_paths[index],
            "value": _value_to_wire(qualified_value.value),
            "quality": str(qualified_value.quality),
            "timestamp": system.date.format(
                qualified_value.timestamp,
                "yyyy-MM-dd'T'HH:mm:ss.SSSXXX",
            ) if qualified_value.timestamp is not None else None,
        })
    return {"ok": True, "values": values}


def _tag_write_blocking(payload):
    tag_paths = _required_list(payload, "tagPaths")
    values = _required_list(payload, "values")
    if len(tag_paths) != len(values):
        raise BadRequest("tagPaths and values must have the same length")
    timeout_ms = int(payload.get("timeoutMs") or 45000)
    quality_codes = system.tag.writeBlocking(tag_paths, values, timeout_ms)
    return {
        "ok": True,
        "qualities": [
            {"tagPath": tag_paths[index], "quality": str(quality)}
            for index, quality in enumerate(quality_codes)
        ],
    }


def _tag_configure(payload):
    base_path = payload.get("basePath")
    if not isinstance(base_path, basestring):
        raise BadRequest("Request must include basePath string")
    tags = _required_list(payload, "tags")
    collision_policy = payload.get("collisionPolicy") or "o"
    quality_codes = system.tag.configure(base_path, tags, collision_policy)
    qualities = []
    for index, quality in enumerate(quality_codes):
        name = tags[index].get("name") if index < len(tags) and isinstance(tags[index], dict) else None
        qualities.append({"name": name, "quality": str(quality)})
    return {"ok": True, "qualities": qualities}


def _tag_delete(payload):
    tag_paths = _required_list(payload, "tagPaths")
    quality_codes = system.tag.deleteTags(tag_paths)
    return {
        "ok": True,
        "qualities": [
            {"tagPath": tag_paths[index], "quality": str(quality)}
            for index, quality in enumerate(quality_codes)
        ],
    }


def _browse_result_to_wire(result):
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
        if value is not None:
            item[key] = bool(value) if key == "hasChildren" else str(value)
    return item


def _tag_browse(payload):
    path = payload.get("path")
    if not isinstance(path, basestring):
        raise BadRequest("Request must include path string")
    browse_filter = payload.get("filter") or {}
    if not isinstance(browse_filter, dict):
        raise BadRequest("filter must be an object")
    results = system.tag.browse(path, browse_filter).getResults()
    return {"ok": True, "results": [_browse_result_to_wire(result) for result in results]}


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


def _config_to_wire(config):
    item = {}
    for key in [
        "name",
        "tagType",
        "valueSource",
        "dataType",
        "value",
        "historyEnabled",
        "historyProvider",
        "historySampleMode",
        "historySampleRate",
        "historySampleRateUnits",
        "historicalDeadband",
        "historicalDeadbandMode",
    ]:
        value = _config_value(config, key)
        if value is not None:
            item[key] = value
    children = _config_value(config, "tags")
    if children is not None:
        item["tags"] = [_config_to_wire(child) for child in children]
    return item


def _tag_get_configuration(payload):
    path = payload.get("path")
    paths = payload.get("paths")
    recursive = bool(payload.get("recursive", False))
    if paths is not None:
        if not isinstance(paths, list):
            raise BadRequest("paths must be a list")
        configs = []
        for current_path in paths:
            if not isinstance(current_path, basestring):
                raise BadRequest("paths must contain path strings")
            configs.extend([_config_to_wire(config) for config in system.tag.getConfiguration(current_path, recursive)])
    else:
        if not isinstance(path, basestring):
            raise BadRequest("Request must include path string")
        configs = [_config_to_wire(config) for config in system.tag.getConfiguration(path, recursive)]
    return {"ok": True, "configs": configs}


def _historian_browse_result_to_wire(result):
    row = {
        "path": str(result.getPath()),
        "displayPath": None,
        "hasChildren": bool(result.hasChildren()),
        "type": None,
        "metadata": None,
    }
    try:
        display_path = result.getDisplayPath()
    except (AttributeError, TypeError):
        display_path = None
    if display_path is not None:
        row["displayPath"] = str(display_path)
    if result.getType() is not None:
        row["type"] = str(result.getType())
    try:
        metadata = result.getMetadata()
    except (AttributeError, TypeError):
        metadata = None
    if metadata is not None:
        row["metadata"] = str(metadata)
    return row


def _historian_browse(payload):
    path = payload.get("path")
    if not isinstance(path, basestring):
        raise BadRequest("Request must include path string")
    continuation = payload.get("continuationPoint")
    results = system.historian.browse(path, continuation) if continuation else system.historian.browse(path)
    if results is None:
        return {"ok": True, "results": [], "continuationPoint": None, "quality": "Unavailable"}
    continuation_point = results.getContinuationPoint()
    return {
        "ok": True,
        "results": [_historian_browse_result_to_wire(result) for result in results.getResults()],
        "continuationPoint": str(continuation_point) if continuation_point is not None else None,
        "quality": str(results.getResultQuality()),
    }


def _historian_browse_paths(path):
    historian = getattr(system, "historian", None)
    browse = getattr(historian, "browse", None) if historian is not None else None
    if browse is None:
        raise BadRequest("Ignition historian browse capability is unavailable")
    results = browse(path)
    if results is None:
        return []
    values = results.getResults()
    if values is None:
        return []
    paths = []
    for result in values:
        try:
            value = result.getPath()
        except Exception:
            value = None
        if value is not None:
            paths.append(str(value))
    return paths


def _history_route_candidates():
    candidates = []
    try:
        provider_roots = _historian_browse_paths("")
    except Exception:
        provider_roots = []
    for provider_root in provider_roots:
        if not provider_root.startswith("histprov:"):
            continue
        try:
            children = _historian_browse_paths(provider_root)
        except Exception:
            continue
        for path in children:
            if ":/drv:" in path and ":/tag:" not in path:
                candidates.append(path.rstrip("/"))
    return candidates


def _refresh_history_routes(tag_providers):
    import time
    now = time.time()
    candidates = _history_route_candidates()
    for tag_provider in tag_providers:
        suffix = ":" + tag_provider
        matches = [path for path in candidates if path.split(":/drv:", 1)[1].endswith(suffix)]
        if len(matches) != 1:
            _HISTORY_ROUTE_CACHE.pop(tag_provider, None)
            raise BadRequest("No unique historical driver route for tag provider %s" % tag_provider)
        if len(_HISTORY_ROUTE_CACHE) >= _HISTORY_ROUTE_CACHE_MAX_PROVIDERS:
            oldest = min(_HISTORY_ROUTE_CACHE.items(), key=lambda item: item[1][0])[0]
            _HISTORY_ROUTE_CACHE.pop(oldest, None)
        _HISTORY_ROUTE_CACHE[tag_provider] = (now, matches[0])


def _resolve_history_paths(paths):
    import time
    now = time.time()
    providers = []
    for item in paths:
        tagpath = item["tagpath"]
        if not tagpath.startswith("histprov:") and tagpath.startswith("[") and "]" in tagpath:
            provider = tagpath[1:tagpath.find("]")]
            cached = _HISTORY_ROUTE_CACHE.get(provider)
            if provider and provider not in providers and (
                cached is None or now - cached[0] >= _HISTORY_ROUTE_CACHE_TTL_SECONDS
            ):
                providers.append(provider)
    if providers:
        _refresh_history_routes(providers)
    resolved = []
    for item in paths:
        tagpath = item["tagpath"]
        if tagpath.startswith("histprov:"):
            resolved.append(tagpath)
            continue
        if not tagpath.startswith("[") or "]" not in tagpath:
            raise BadRequest("tagpath must be fully qualified as [provider]relative/path")
        provider_end = tagpath.find("]")
        provider = tagpath[1:provider_end]
        relative = tagpath[provider_end + 1:].lstrip("/")
        if not provider or not relative:
            raise BadRequest("tagpath must include a provider and relative path")
        resolved.append(_HISTORY_ROUTE_CACHE[provider][1] + ":/tag:" + relative)
    return resolved


def _history_resolution_supported():
    historian = getattr(system, "historian", None)
    return historian is not None and getattr(historian, "browse", None) is not None


def _historian_store_data_points(payload):
    paths = _required_list(payload, "paths")
    values = _required_list(payload, "values")
    timestamps = _required_list(payload, "timestamps")
    qualities = payload.get("qualities") or [192 for path in paths]
    if len(paths) != len(values) or len(paths) != len(timestamps) or len(paths) != len(qualities):
        raise BadRequest("paths, values, timestamps, and qualities must have the same length")
    dates = [system.date.fromMillis(long(timestamp)) for timestamp in timestamps]
    result = system.historian.storeDataPoints(paths, values, dates, qualities)
    try:
        quality_strings = [str(quality) for quality in result]
    except Exception:
        quality_strings = [str(result)]
    return {"ok": True, "qualities": quality_strings}


def _historian_query_raw_points(payload):
    paths = _required_list(payload, "paths")
    start_time = payload.get("startTime")
    end_time = payload.get("endTime")
    if start_time is None or end_time is None:
        raise BadRequest("Request must include startTime and endTime")
    return_size = int(payload.get("returnSize") or 100)
    column_names = ["value_%d" % index for index in range(len(paths))]
    dataset = system.historian.queryRawPoints(
        paths,
        system.date.fromMillis(long(start_time)),
        system.date.fromMillis(long(end_time)),
        column_names,
        "TALL",
        return_size,
        False,
    )
    return {
        "ok": True,
        "result": _dataset_to_wire(dataset),
        "resultSource": "ignition.dataset",
        "resultMessage": "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings",
    }


def _history_value_type(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, long, float)):
        return "number"
    if isinstance(value, basestring):
        return "string"
    return "object" if isinstance(value, dict) else "array" if isinstance(value, (list, tuple)) else "string"


def _history_fingerprint(paths, start, end):
    import hashlib
    canonical = "%s\n%s\n%s" % (
        start, end, "\n".join(["%s\0%s" % (item["seriesKey"], item["tagpath"]) for item in paths]),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _history_cursor_encode(fingerprint, offset, identity):
    import base64
    raw = system.util.jsonEncode({
        "v": 2, "f": fingerprint, "o": offset, "t": identity[0], "s": identity[1],
    })
    encoded = base64.urlsafe_b64encode(raw.encode("utf-8"))
    if not isinstance(encoded, basestring):
        encoded = encoded.decode("ascii")
    return encoded.rstrip("=")


def _history_cursor_decode(cursor, fingerprint):
    import base64
    if not isinstance(cursor, basestring) or not cursor or len(cursor) > 1024:
        raise BadRequest("cursor must be a non-empty opaque string")
    try:
        padded = cursor + ("=" * ((4 - len(cursor) % 4) % 4))
        token = system.util.jsonDecode(base64.urlsafe_b64decode(padded))
        if not isinstance(token, dict) or token.get("v") != 2 or token.get("f") != fingerprint:
            raise ValueError("mismatch")
        timestamp = long(token["t"])
        series_key = token["s"]
        if not isinstance(series_key, basestring):
            raise ValueError("series")
        offset = int(token["o"])
        if offset < 1:
            raise ValueError("offset")
        return offset, (timestamp, series_key)
    except Exception:
        raise BadRequest("cursor is malformed or does not match this request")


def _history_request(payload):
    paths = payload.get("paths")
    if not isinstance(paths, list) or not paths or len(paths) > 20:
        raise BadRequest("paths must contain between 1 and 20 items")
    normalized = []
    seen = {}
    for item in paths:
        if not isinstance(item, dict) or set(item.keys()) != set(["seriesKey", "tagpath"]):
            raise BadRequest("each path must contain only seriesKey and tagpath")
        series_key = item.get("seriesKey")
        tagpath = item.get("tagpath")
        if not isinstance(series_key, basestring) or not series_key or not isinstance(tagpath, basestring) or not tagpath:
            raise BadRequest("seriesKey and tagpath must be non-empty strings")
        if series_key in seen:
            raise BadRequest("seriesKey values must be unique")
        seen[series_key] = True
        normalized.append({"seriesKey": series_key, "tagpath": tagpath})
    try:
        start = long(payload["start"])
        end = long(payload["end"])
        limit = int(payload.get("limit", 1000))
    except Exception:
        raise BadRequest("start, end, and limit must be integers")
    if start >= end or end - start > 86400000:
        raise BadRequest("interval must be non-empty and no longer than 86400000 ms")
    if limit < 1 or limit > 10000:
        raise BadRequest("limit must be between 1 and 10000")
    allowed = set(["paths", "start", "end", "limit", "cursor"])
    if set(payload.keys()) - allowed:
        raise BadRequest("historian page request contains unsupported fields")
    return normalized, start, end, limit


def _history_admission_count(paths, resolved_paths, start_date, end_date):
    try:
        aliases = [item["seriesKey"] for item in paths]
        dataset = system.tag.queryTagCalculations(
            paths=resolved_paths, calculations=["Count"], aliases=aliases, startDate=start_date,
            endDate=end_date, includeBoundingValues=False, noInterpolation=True,
            ignoreBadQuality=True,
        )
        columns = list(dataset.getColumnNames())
        count_columns = [name for name in columns if str(name).lower() == "count"]
        identity_columns = [name for name in columns if str(name).lower() != "count"]
        if len(count_columns) != 1 or len(identity_columns) != 1:
            raise ValueError("shape")
        count_column = count_columns[0]
        identity_column = identity_columns[0]
        expected = {}
        for alias in aliases:
            expected[alias] = expected.get(alias, 0) + 1
        if len(expected) != len(aliases):
            raise ValueError("duplicate alias")
        seen = {}
        total = 0
        for row_index in range(dataset.getRowCount()):
            alias = str(dataset.getValueAt(row_index, identity_column))
            if alias not in expected or alias in seen:
                raise ValueError("alias")
            count = dataset.getValueAt(row_index, count_column)
            if count is None or isinstance(count, (basestring, bool)):
                raise ValueError("count")
            numeric = long(count)
            if numeric < 0 or float(count) != numeric:
                raise ValueError("count")
            seen[alias] = True
            total += numeric
            if total > _HISTORY_PAGE_MAX_TOTAL_POINTS:
                raise HistorianCountLimitExceeded("historian Count exceeds %d points" % _HISTORY_PAGE_MAX_TOTAL_POINTS)
        return total
    except BadRequest:
        raise
    except Exception:
        raise BadRequest("queryTagCalculations Count is unavailable or malformed")


def _history_materialize(paths, start, end):
    if not _history_resolution_supported():
        raise BadRequest("Ignition historian browse capability is unavailable")
    resolved_paths = _resolve_history_paths(paths)
    start_date = system.date.fromMillis(start)
    end_date = system.date.fromMillis(end)
    _history_admission_count(paths, resolved_paths, start_date, end_date)
    dataset = system.tag.queryTagHistory(
        paths=resolved_paths, startDate=start_date, endDate=end_date, returnSize=-1,
        returnFormat="Tall", columnNames=[item["seriesKey"] for item in paths],
        includeBoundingValues=False, noInterpolation=True, ignoreBadQuality=True,
    )
    columns = list(dataset.getColumnNames())
    by_lower = dict((str(name).lower(), name) for name in columns)
    if any(name not in by_lower for name in ["timestamp", "value", "quality", "path"]):
        raise BadRequest("queryTagHistory returned an unsupported Tall dataset shape")
    path_by_key = dict((item["seriesKey"], item["tagpath"]) for item in paths)
    winners = {}
    for row_index in range(dataset.getRowCount()):
        raw_timestamp = dataset.getValueAt(row_index, by_lower["timestamp"])
        timestamp = long(raw_timestamp.getTime() if hasattr(raw_timestamp, "getTime") else raw_timestamp)
        if timestamp < start or timestamp >= end:
            continue
        series_key = str(dataset.getValueAt(row_index, by_lower["path"]))
        if series_key not in path_by_key:
            raise BadRequest("queryTagHistory returned an unknown Tall path identity")
        value = _value_to_wire(dataset.getValueAt(row_index, by_lower["value"]))
        winners[(timestamp, series_key)] = (
            series_key, path_by_key[series_key], timestamp, value,
            str(dataset.getValueAt(row_index, by_lower["quality"])), _history_value_type(value),
        )
    rows = tuple(winners[key] for key in sorted(winners.keys()))
    size = len(system.util.jsonEncode(rows).encode("utf-8"))
    if size > _HISTORY_PAGE_CACHE_MAX_BYTES:
        raise BadRequest("normalized historian result exceeds snapshot byte limit")
    return rows, size


def _historian_page(payload):
    paths, start, end, limit = _history_request(payload)
    fingerprint = _history_fingerprint(paths, start, end)
    cursor = _history_cursor_decode(payload["cursor"], fingerprint) if payload.get("cursor") is not None else None
    import time
    owner = False
    inflight = None
    with _HISTORY_PAGE_CACHE_LOCK:
        now = time.time()
        for key in list(_HISTORY_PAGE_CACHE_ORDER):
            if now - _HISTORY_PAGE_CACHE[key][0] >= _HISTORY_PAGE_CACHE_TTL_SECONDS:
                _HISTORY_PAGE_CACHE.pop(key, None)
                _HISTORY_PAGE_CACHE_ORDER.remove(key)
        snapshot = _HISTORY_PAGE_CACHE.get(fingerprint)
        if cursor is not None and snapshot is None:
            raise BadRequest("cursor snapshot is missing or expired")
        if snapshot is None:
            inflight = _HISTORY_PAGE_INFLIGHT.get(fingerprint)
            if inflight is None:
                inflight = {"event": threading.Event(), "waiters": 0, "snapshot": None, "error": None}
                _HISTORY_PAGE_INFLIGHT[fingerprint] = inflight
                owner = True
            else:
                inflight["waiters"] += 1
        elif fingerprint in _HISTORY_PAGE_CACHE_ORDER:
            _HISTORY_PAGE_CACHE_ORDER.remove(fingerprint)
            _HISTORY_PAGE_CACHE_ORDER.append(fingerprint)
    if snapshot is None:
        if owner:
            try:
                rows, size = _history_materialize(paths, start, end)
                snapshot = (time.time(), rows, size)
            except Exception as error:
                with _HISTORY_PAGE_CACHE_LOCK:
                    inflight["error"] = error
                    inflight["event"].set()
                    if not inflight["waiters"]:
                        _HISTORY_PAGE_INFLIGHT.pop(fingerprint, None)
                raise
            with _HISTORY_PAGE_CACHE_LOCK:
                inflight["snapshot"] = snapshot
                if len(rows) > 1:
                    while _HISTORY_PAGE_CACHE_ORDER and (
                        len(_HISTORY_PAGE_CACHE_ORDER) >= _HISTORY_PAGE_CACHE_MAX_WINDOWS or
                        sum(_HISTORY_PAGE_CACHE[key][2] for key in _HISTORY_PAGE_CACHE_ORDER) + size > _HISTORY_PAGE_CACHE_MAX_BYTES or
                        sum(len(_HISTORY_PAGE_CACHE[key][1]) for key in _HISTORY_PAGE_CACHE_ORDER) + len(rows) > _HISTORY_PAGE_CACHE_MAX_POINTS
                    ):
                        oldest = _HISTORY_PAGE_CACHE_ORDER.pop(0)
                        _HISTORY_PAGE_CACHE.pop(oldest, None)
                    _HISTORY_PAGE_CACHE[fingerprint] = snapshot
                    _HISTORY_PAGE_CACHE_ORDER.append(fingerprint)
                inflight["event"].set()
                if not inflight["waiters"]:
                    _HISTORY_PAGE_INFLIGHT.pop(fingerprint, None)
        else:
            inflight["event"].wait()
            with _HISTORY_PAGE_CACHE_LOCK:
                snapshot = inflight["snapshot"]
                error = inflight["error"]
                inflight["waiters"] -= 1
                if not inflight["waiters"]:
                    _HISTORY_PAGE_INFLIGHT.pop(fingerprint, None)
            if error is not None:
                raise error
    with _HISTORY_PAGE_CACHE_LOCK:
        rows = snapshot[1]
        offset = cursor[0] if cursor is not None else 0
        if cursor is not None and (offset > len(rows) or (rows[offset - 1][2], rows[offset - 1][0]) != cursor[1]):
            raise BadRequest("cursor does not identify the cached page boundary")
        page_rows = rows[offset:offset + limit]
        next_offset = offset + len(page_rows)
        complete = next_offset >= len(rows)
    points = [{"seriesKey": row[0], "tagpath": row[1], "timestamp": row[2], "value": row[3],
               "quality": row[4], "valueType": row[5]} for row in page_rows]
    return {
        "ok": True, "protocolVersion": 1, "paths": paths, "start": start, "end": end,
        "points": points, "complete": complete,
        "nextCursor": None if complete else _history_cursor_encode(
            fingerprint, next_offset, (page_rows[-1][2], page_rows[-1][0])),
    }


def _capabilities(payload):
    supported = _history_resolution_supported()
    return {"ok": True, "protocolVersion": 1, "historianStream": {
        "supported": True, "protocolVersion": 1, "format": "ndjson-columnar-blocks",
        "interval": "[start,end)", "maxPaths": 20, "maxWindowMs": 86400000,
        "maxBlockRows": 5000, "maxBlockBytes": 1048576, "maxResponseBytes": 67108864,
        "maxDurationMs": 120000, "qualityPolicy": "all qualities retained",
    }, "historianPage": {
        "supported": supported, "exactRawCapture": supported, "input": "paths[{seriesKey,tagpath}]",
        "interval": "[start,end)", "defaultLimit": 1000, "maxLimit": 10000,
        "maxPaths": 20, "maxWindowMs": 86400000, "maxTotalPoints": 10000,
        "snapshotTtlMs": 20000, "ordering": "timestamp,seriesKey",
        "equalTimestampPaging": "composite-cursor",
        "admission": "queryTagCalculations Count; fail closed; conservative before timestamp dedupe",
        "qualityPolicy": "ignoreBadQuality=true; only Ignition Good/192-eligible samples",
        "tagpathResolution": "Ignition historical namespace resolves [provider]relative/path to one driver route",
        "winnerPolicy": "last queryTagHistory Tall row wins per (seriesKey,timestamp)",
    }}


_OPERATIONS = {
    "capabilities": _capabilities,
    "util/getVersion": _util_get_version,
    "util/queryAuditLog": _util_query_audit_log,
    "tag/readBlocking": _tag_read_blocking,
    "tag/writeBlocking": _tag_write_blocking,
    "tag/configure": _tag_configure,
    "tag/deleteTags": _tag_delete,
    "tag/browse": _tag_browse,
    "tag/getConfiguration": _tag_get_configuration,
    "historian/browse": _historian_browse,
    "historian/page": _historian_page,
    "historian/storeDataPoints": _historian_store_data_points,
    "historian/queryRawPoints": _historian_query_raw_points,
}


def dispatch(operation, payload_json):
    try:
        handler = _OPERATIONS.get(operation)
        if handler is None:
            return system.util.jsonEncode({
                "status": 404,
                "body": {"ok": False, "error": "Unsupported Fluxy operation"},
            })
        payload = system.util.jsonDecode(payload_json or "{}")
        if not isinstance(payload, dict):
            raise BadRequest("Request body must be a JSON object")
        return system.util.jsonEncode({"status": 200, "body": handler(payload)})
    except HistorianCountLimitExceeded, exc:
        return system.util.jsonEncode({
            "status": 400,
            "body": {"ok": False, "code": "HISTORIAN_COUNT_LIMIT_EXCEEDED", "error": str(exc)},
        })
    except BadRequest, exc:
        return system.util.jsonEncode({
            "status": 400,
            "body": {"ok": False, "error": str(exc)},
        })
    except Conflict, exc:
        return system.util.jsonEncode({
            "status": 409,
            "body": {"ok": False, "code": "HISTORIAN_PAGE_UNSUPPORTED", "error": str(exc)},
        })
    except Exception, exc:
        system.util.getLogger("Fluxy.Module.Dispatch").error("%s failed: %s" % (operation, exc))
        return system.util.jsonEncode({
            "status": 500,
            "body": {"ok": False, "error": str(exc)},
        })
