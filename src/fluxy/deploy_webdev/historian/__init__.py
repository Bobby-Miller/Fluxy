from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


DATASET_HELPERS = r'''


def _dataset_to_wire(dataset):
    rows = []
    column_names = list(dataset.getColumnNames())
    for row_index in range(dataset.getRowCount()):
        row = []
        for column_name in column_names:
            value = dataset.getValueAt(row_index, column_name)
            if hasattr(value, "getTime"):
                value = value.getTime()
            row.append(value)
        rows.append(row)
    return {"rows": rows, "columns": column_names}
'''


HISTORIAN_COMPAT_HELPERS = r'''


def _is_ignition_83_or_newer():
    version = system.util.getVersion()
    major = getattr(version, "major", None)
    minor = getattr(version, "minor", None)
    try:
        return int(major) > 8 or (int(major) == 8 and int(minor) >= 3)
    except Exception:
        parts = str(version).split(".")
        if len(parts) < 2:
            return False
        return int(parts[0]) > 8 or (int(parts[0]) == 8 and int(parts[1]) >= 3)


def _historical_tag_parts(path):
    if not isinstance(path, basestring) or not path.startswith("histprov:"):
        raise ValueError("8.1 historian fallback requires a historical path starting with histprov:")
    provider_end = path.find(":/")
    if provider_end < 0:
        raise ValueError("Historical path is missing provider separator: %s" % path)
    history_provider = path[len("histprov:"):provider_end]
    tag_marker = ":/tag:"
    tag_index = path.find(tag_marker)
    if tag_index < 0:
        raise ValueError("Historical path is missing /tag: section: %s" % path)
    tag_path = path[tag_index + len(tag_marker):]
    provider_marker = ":/prov:"
    provider_index = path.find(provider_marker)
    if provider_index >= 0 and provider_index < tag_index:
        tag_provider = path[provider_index + len(provider_marker):tag_index]
        return history_provider, tag_provider, tag_path
    driver_marker = ":/drv:"
    driver_index = path.find(driver_marker)
    if driver_index >= 0 and driver_index < tag_index:
        driver = path[driver_index + len(driver_marker):tag_index]
        if ":" in driver:
            return history_provider, driver.split(":", 1)[1], tag_path
    raise ValueError("Historical path is missing /prov: or /drv: provider section: %s" % path)


def _store_tag_history_81(paths, values, timestamps, qualities):
    grouped = {}
    for index, path in enumerate(paths):
        history_provider, tag_provider, tag_path = _historical_tag_parts(path)
        key = (history_provider, tag_provider)
        if key not in grouped:
            grouped[key] = {"paths": [], "values": [], "qualities": [], "timestamps": []}
        grouped[key]["paths"].append(tag_path)
        grouped[key]["values"].append(values[index])
        grouped[key]["qualities"].append(qualities[index])
        grouped[key]["timestamps"].append(timestamps[index])
    for key, group in grouped.items():
        system.tag.storeTagHistory(
            key[0],
            key[1],
            group["paths"],
            group["values"],
            group["qualities"],
            _dates_from_millis(group["timestamps"]),
        )


def _quality_list_to_wire(value):
    try:
        return [str(quality) for quality in value]
    except Exception:
        return [str(value)]


def _optional_to_wire(value):
    if value is None:
        return None
    try:
        if value.isPresent():
            return str(value.get())
        return None
    except Exception:
        return str(value)


def _annotation_to_wire(annotation):
    value = annotation.value()
    return {
        "storageId": str(annotation.identifier()),
        "path": str(annotation.source()),
        "startTime": str(annotation.startTime()),
        "endTime": _optional_to_wire(annotation.endTime()),
        "type": str(value.type()),
        "data": str(value.notes()),
        "author": str(value.author()),
    }


def _property_set_to_wire(properties):
    out = {}
    for prop in properties.getProperties():
        name = str(prop.getName())
        value = properties.get(prop)
        if value is not None and not isinstance(value, (basestring, int, long, float, bool)):
            value = str(value)
        out[name] = value
    return out


def _metadata_to_wire(metadata):
    return {
        "path": str(metadata.source()),
        "timestamp": str(metadata.timestamp()),
        "quality": str(metadata.quality()),
        "properties": _property_set_to_wire(metadata.value()),
    }
'''


BROWSE_POST = COMMON + HISTORIAN_COMPAT_HELPERS + r'''


def _browse_result_to_wire(result):
    row = {
        "path": str(result.getPath()),
        "displayPath": None,
        "hasChildren": bool(result.hasChildren()),
        "type": None,
        "metadata": None,
    }
    display_path = result.getDisplayPath()
    result_type = result.getType()
    metadata = result.getMetadata()
    if display_path is not None:
        row["displayPath"] = str(display_path)
    if result_type is not None:
        row["type"] = str(result_type)
    if metadata is not None:
        row["metadata"] = str(metadata)
    return row


def doPost(request, session):
    operation = "Historian.browse"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        path = payload.get("path")
        continuation_point = payload.get("continuationPoint") or payload.get("continuation_point")
        if not path:
            return _bad_request("Request must include path", _request_debug(request))
        if _is_ignition_83_or_newer():
            if continuation_point:
                browse_results = system.historian.browse(path, continuation_point)
            else:
                browse_results = system.historian.browse(path)
        else:
            if continuation_point:
                browse_results = system.tag.browseHistoricalTags(path, None, None, continuation_point)
            else:
                browse_results = system.tag.browseHistoricalTags(path)
        rows = [_browse_result_to_wire(result) for result in browse_results.getResults()]
        continuation = browse_results.getContinuationPoint()
        quality = browse_results.getResultQuality()
        if continuation is not None:
            continuation = str(continuation)
        _log_success(operation)
        return {"json": {"ok": True, "results": rows, "continuationPoint": continuation, "quality": str(quality)}}
    except Exception, exc:
        _log_error(operation, "browse failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


STORE_DATA_POINTS_POST = COMMON + HISTORIAN_COMPAT_HELPERS + r'''


def _dates_from_millis(values):
    return [system.date.fromMillis(long(value)) for value in values]


def doPost(request, session):
    operation = "Historian.storeDataPoints"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        paths = payload.get("paths")
        values = payload.get("values")
        timestamps = payload.get("timestamps")
        qualities = payload.get("qualities") or [192 for _path in paths]
        if not isinstance(paths, list):
            return _bad_request("Request must include paths list", _request_debug(request))
        if not isinstance(values, list):
            return _bad_request("Request must include values list", _request_debug(request))
        if not isinstance(timestamps, list):
            return _bad_request("Request must include timestamps list", _request_debug(request))
        if len(paths) != len(values) or len(paths) != len(timestamps) or len(paths) != len(qualities):
            return _bad_request("paths, values, timestamps, and qualities must have the same length", _request_debug(request))
        if _is_ignition_83_or_newer():
            quality_codes = system.historian.storeDataPoints(paths, values, _dates_from_millis(timestamps), qualities)
            quality_strings = _quality_list_to_wire(quality_codes)
        else:
            _store_tag_history_81(paths, values, timestamps, qualities)
            quality_strings = ["Good" for _path in paths]
        _log_success(operation)
        return {"json": {"ok": True, "qualities": quality_strings}}
    except Exception, exc:
        _log_error(operation, "storeDataPoints failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


STORE_ANNOTATIONS_POST = COMMON + HISTORIAN_COMPAT_HELPERS + r'''


def _dates_or_none_from_millis(values):
    if values is None:
        return None
    return [system.date.fromMillis(long(value)) for value in values]


def doPost(request, session):
    operation = "Historian.storeAnnotations"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        paths = payload.get("paths")
        start_times = payload.get("startTimes") or payload.get("start_times")
        end_times = payload.get("endTimes") or payload.get("end_times")
        types = payload.get("types")
        data = payload.get("data")
        storage_ids = payload.get("storageIds") or payload.get("storage_ids")
        deleted = payload.get("deleted")
        if not isinstance(paths, list):
            return _bad_request("Request must include paths list", _request_debug(request))
        if not isinstance(start_times, list):
            return _bad_request("Request must include startTimes list", _request_debug(request))
        start_dates = _dates_or_none_from_millis(start_times)
        end_dates = _dates_or_none_from_millis(end_times)
        if _is_ignition_83_or_newer():
            if deleted is not None:
                qualities = system.historian.storeAnnotations(paths, start_dates, end_dates, types, data, storage_ids, deleted)
            elif storage_ids is not None:
                qualities = system.historian.storeAnnotations(paths, start_dates, end_dates, types, data, storage_ids)
            elif data is not None:
                qualities = system.historian.storeAnnotations(paths, start_dates, end_dates, types, data)
            elif types is not None:
                qualities = system.historian.storeAnnotations(paths, start_dates, end_dates, types)
            elif end_times is not None:
                qualities = system.historian.storeAnnotations(paths, start_dates, end_dates)
            else:
                qualities = system.historian.storeAnnotations(paths, start_dates)
        else:
            if deleted is not None:
                qualities = system.tag.storeAnnotations(paths, start_dates, end_dates, types, data, storage_ids, deleted)
            elif storage_ids is not None:
                qualities = system.tag.storeAnnotations(paths, start_dates, end_dates, types, data, storage_ids)
            elif data is not None:
                qualities = system.tag.storeAnnotations(paths, start_dates, end_dates, types, data)
            elif types is not None:
                qualities = system.tag.storeAnnotations(paths, start_dates, end_dates, types)
            elif end_times is not None:
                qualities = system.tag.storeAnnotations(paths, start_dates, end_dates)
            else:
                qualities = system.tag.storeAnnotations(paths, start_dates)
        _log_success(operation)
        return {"json": {"ok": True, "qualities": _quality_list_to_wire(qualities)}}
    except Exception, exc:
        _log_error(operation, "storeAnnotations failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


QUERY_ANNOTATIONS_POST = COMMON + HISTORIAN_COMPAT_HELPERS + r'''


def doPost(request, session):
    operation = "Historian.queryAnnotations"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        paths = payload.get("paths")
        start_date = payload.get("startDate") or payload.get("start_date")
        end_date = payload.get("endDate") or payload.get("end_date")
        allowed_types = payload.get("allowedTypes") or payload.get("allowed_types")
        if not isinstance(paths, list):
            return _bad_request("Request must include paths list", _request_debug(request))
        if start_date is None:
            return _bad_request("Request must include startDate", _request_debug(request))
        if _is_ignition_83_or_newer():
            results = system.historian.queryAnnotations(
                paths,
                system.date.fromMillis(long(start_date)),
                system.date.fromMillis(long(end_date)) if end_date is not None else None,
                allowed_types,
            )
        else:
            results = system.tag.queryAnnotations(
                paths,
                system.date.fromMillis(long(start_date)),
                system.date.fromMillis(long(end_date)) if end_date is not None else None,
                allowed_types,
            )
        annotations = [_annotation_to_wire(annotation) for annotation in results.getResults()]
        _log_success(operation)
        return {"json": {"ok": True, "annotations": annotations, "quality": str(results.getResultQuality())}}
    except Exception, exc:
        _log_error(operation, "queryAnnotations failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


DELETE_ANNOTATIONS_POST = COMMON + HISTORIAN_COMPAT_HELPERS + r'''


def doPost(request, session):
    operation = "Historian.deleteAnnotations"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        paths = payload.get("paths")
        storage_ids = payload.get("storageIds") or payload.get("storage_ids")
        if not isinstance(paths, list):
            return _bad_request("Request must include paths list", _request_debug(request))
        if not isinstance(storage_ids, list):
            return _bad_request("Request must include storageIds list", _request_debug(request))
        if _is_ignition_83_or_newer():
            qualities = system.historian.deleteAnnotations(paths, storage_ids)
        else:
            qualities = system.tag.deleteAnnotations(paths, storage_ids)
        _log_success(operation)
        return {"json": {"ok": True, "qualities": _quality_list_to_wire(qualities)}}
    except Exception, exc:
        _log_error(operation, "deleteAnnotations failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


STORE_METADATA_POST = COMMON + HISTORIAN_COMPAT_HELPERS + r'''


def _dates_from_millis(values):
    return [system.date.fromMillis(long(value)) for value in values]


def doPost(request, session):
    operation = "Historian.storeMetadata"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        if not _is_ignition_83_or_newer():
            return {"json": {"ok": False, "error": "system.historian.storeMetadata requires Ignition 8.3+"}, "status": 400}
        payload = _json_body(request)
        paths = payload.get("paths")
        timestamps = payload.get("timestamps")
        properties = payload.get("properties")
        if not isinstance(paths, list):
            return _bad_request("Request must include paths list", _request_debug(request))
        if not isinstance(timestamps, list):
            return _bad_request("Request must include timestamps list", _request_debug(request))
        if not isinstance(properties, dict):
            return _bad_request("Request must include properties object", _request_debug(request))
        qualities = system.historian.storeMetadata(paths, _dates_from_millis(timestamps), properties)
        _log_success(operation)
        return {"json": {"ok": True, "qualities": _quality_list_to_wire(qualities)}}
    except Exception, exc:
        _log_error(operation, "storeMetadata failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


QUERY_METADATA_POST = COMMON + HISTORIAN_COMPAT_HELPERS + r'''


def doPost(request, session):
    operation = "Historian.queryMetadata"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        if not _is_ignition_83_or_newer():
            return {"json": {"ok": False, "error": "system.historian.queryMetadata requires Ignition 8.3+"}, "status": 400}
        payload = _json_body(request)
        paths = payload.get("paths")
        start_date = payload.get("startDate") or payload.get("start_date")
        end_date = payload.get("endDate") or payload.get("end_date")
        if not isinstance(paths, list):
            return _bad_request("Request must include paths list", _request_debug(request))
        if end_date is not None and start_date is None:
            return _bad_request("startDate is required when endDate is supplied", _request_debug(request))
        if end_date is not None:
            results = system.historian.queryMetadata(paths, system.date.fromMillis(long(start_date)), system.date.fromMillis(long(end_date)))
        elif start_date is not None:
            results = system.historian.queryMetadata(paths, system.date.fromMillis(long(start_date)))
        else:
            results = system.historian.queryMetadata(paths)
        metadata = [_metadata_to_wire(row) for row in results.getResults()]
        _log_success(operation)
        return {"json": {"ok": True, "metadata": metadata, "quality": str(results.getResultQuality())}}
    except Exception, exc:
        _log_error(operation, "queryMetadata failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


QUERY_RAW_POINTS_POST = COMMON + DATASET_HELPERS + HISTORIAN_COMPAT_HELPERS + r'''


def doPost(request, session):
    operation = "Historian.queryRawPoints"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        paths = payload.get("paths")
        start_time = payload.get("startTime") or payload.get("start_time")
        end_time = payload.get("endTime") or payload.get("end_time")
        return_size = int(payload.get("returnSize") or payload.get("return_size") or 100)
        if not isinstance(paths, list):
            return _bad_request("Request must include paths list", _request_debug(request))
        if start_time is None or end_time is None:
            return _bad_request("Request must include startTime and endTime", _request_debug(request))
        column_names = ["value_%d" % index for index in range(len(paths))]
        if _is_ignition_83_or_newer():
            dataset = system.historian.queryRawPoints(
                paths,
                system.date.fromMillis(long(start_time)),
                system.date.fromMillis(long(end_time)),
                column_names,
                "TALL",
                return_size,
                False,
            )
        else:
            dataset = system.tag.queryTagHistory(
                paths=paths,
                startDate=system.date.fromMillis(long(start_time)),
                endDate=system.date.fromMillis(long(end_time)),
                returnSize=return_size,
                aggregationMode="LastValue",
                returnFormat="Tall",
                columnNames=column_names,
                includeBoundingValues=False,
                noInterpolation=True,
            )
        _log_success(operation)
        return {"json": {"ok": True, "result": _dataset_to_wire(dataset), "resultSource": "ignition.dataset", "resultMessage": "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings"}}
    except Exception, exc:
        _log_error(operation, "queryRawPoints failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


QUERY_AGGREGATED_POINTS_POST = COMMON + DATASET_HELPERS + HISTORIAN_COMPAT_HELPERS + r'''


def doPost(request, session):
    operation = "Historian.queryAggregatedPoints"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        paths = payload.get("paths")
        start_time = payload.get("startTime") or payload.get("start_time")
        end_time = payload.get("endTime") or payload.get("end_time")
        aggregates = payload.get("aggregates")
        fill_modes = payload.get("fillModes") or payload.get("fill_modes")
        column_names = payload.get("columnNames") or payload.get("column_names")
        return_format = payload.get("returnFormat") or payload.get("return_format") or "WIDE"
        return_size = int(payload.get("returnSize") or payload.get("return_size") or 1)
        include_bounds = bool(payload.get("includeBounds") if payload.get("includeBounds") is not None else payload.get("include_bounds") or False)
        exclude_observations = bool(payload.get("excludeObservations") if payload.get("excludeObservations") is not None else payload.get("exclude_observations") or False)
        if not isinstance(paths, list):
            return _bad_request("Request must include paths list", _request_debug(request))
        if start_time is None or end_time is None:
            return _bad_request("Request must include startTime and endTime", _request_debug(request))
        if column_names is None:
            column_names = ["value_%d" % index for index in range(len(paths))]
        if _is_ignition_83_or_newer():
            dataset = system.historian.queryAggregatedPoints(
                paths,
                system.date.fromMillis(long(start_time)),
                system.date.fromMillis(long(end_time)),
                aggregates,
                fill_modes,
                column_names,
                return_format,
                return_size,
                include_bounds,
                exclude_observations,
            )
        else:
            dataset = system.tag.queryTagHistory(
                paths=paths,
                startDate=system.date.fromMillis(long(start_time)),
                endDate=system.date.fromMillis(long(end_time)),
                returnSize=return_size,
                aggregationModes=aggregates,
                returnFormat=return_format,
                columnNames=column_names,
                includeBoundingValues=include_bounds,
                noInterpolation=True,
            )
        _log_success(operation)
        return {"json": {"ok": True, "result": _dataset_to_wire(dataset), "resultSource": "ignition.dataset", "resultMessage": "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings"}}
    except Exception, exc:
        _log_error(operation, "queryAggregatedPoints failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
'''


RESOURCES = [
    WebDevResource("historian/browse", "browse", BROWSE_POST),
    WebDevResource("historian/storeDataPoints", "storeDataPoints", STORE_DATA_POINTS_POST),
    WebDevResource("historian/queryRawPoints", "queryRawPoints", QUERY_RAW_POINTS_POST),
    WebDevResource("historian/queryAggregatedPoints", "queryAggregatedPoints", QUERY_AGGREGATED_POINTS_POST),
    WebDevResource("historian/storeAnnotations", "storeAnnotations", STORE_ANNOTATIONS_POST),
    WebDevResource("historian/queryAnnotations", "queryAnnotations", QUERY_ANNOTATIONS_POST),
    WebDevResource("historian/deleteAnnotations", "deleteAnnotations", DELETE_ANNOTATIONS_POST),
    WebDevResource("historian/storeMetadata", "storeMetadata", STORE_METADATA_POST),
    WebDevResource("historian/queryMetadata", "queryMetadata", QUERY_METADATA_POST),
]
