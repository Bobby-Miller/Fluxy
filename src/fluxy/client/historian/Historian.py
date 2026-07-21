from __future__ import annotations

from dataclasses import dataclass
import json
from contextlib import AbstractContextManager
from json import JSONDecodeError
from typing import Any, Iterator, Protocol

import httpx

from fluxy.client.db import QueryResult
from fluxy.client.db.DB import query_result_from_response


class HistorianTransport(Protocol):
    capabilities_path: str
    historian_page_path: str
    historian_stream_path: str
    base_url: str
    timeout: float
    _client: httpx.Client
    historian_browse_path: str
    historian_store_data_points_path: str
    historian_query_raw_points_path: str
    historian_store_annotations_path: str
    historian_query_annotations_path: str
    historian_delete_annotations_path: str
    historian_store_metadata_path: str
    historian_query_metadata_path: str
    historian_query_aggregated_points_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    def _headers(self, *, request_id: str | None = None) -> dict[str, str]: ...


@dataclass(frozen=True)
class HistorianBrowseResult:
    path: str
    display_path: str | None = None
    has_children: bool | None = None
    result_type: str | None = None
    metadata: str | None = None
    payload: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "HistorianBrowseResult":
        return cls(
            path=str(payload.get("path") or ""),
            display_path=payload.get("displayPath"),
            has_children=payload.get("hasChildren"),
            result_type=payload.get("type"),
            metadata=payload.get("metadata"),
            payload=payload,
        )


class HistorianBrowsePage(list[HistorianBrowseResult]):
    def __init__(
        self, rows: list[HistorianBrowseResult], continuation_point: str | None, quality: str | None
    ):
        super().__init__(rows)
        self.continuation_point = continuation_point
        self.quality = quality


@dataclass(frozen=True)
class HistorianPoint:
    series_key: str
    tagpath: str
    timestamp: int
    value: Any
    quality: str
    value_type: str


@dataclass(frozen=True)
class HistorianPage:
    paths: list[HistorianPath]
    start: int
    end: int
    points: list[HistorianPoint]
    complete: bool
    next_cursor: str | None


@dataclass(frozen=True)
class HistorianPath:
    series_key: str
    tagpath: str


@dataclass(frozen=True)
class HistorianPageCapability:
    supported: bool
    exact_raw_capture: bool
    default_limit: int
    max_limit: int
    equal_timestamp_paging: str
    max_paths: int
    max_window_ms: int
    reason: str | None = None
    max_total_points: int | None = None
    stream: HistorianStreamCapability | None = None


@dataclass(frozen=True)
class HistorianStreamCapability:
    supported: bool
    protocol_version: int = 0
    max_block_rows: int = 0
    reason: str | None = None


class HistorianStreamError(RuntimeError):
    """Base error with a stable category for stream retry decisions."""


class HistorianStreamTransientError(HistorianStreamError):
    pass


class HistorianStreamPermanentError(HistorianStreamError):
    pass


class HistorianStreamProtocolError(HistorianStreamPermanentError):
    pass


@dataclass(frozen=True)
class HistorianStreamHeader:
    paths: tuple[HistorianPath, ...]
    start: int
    end: int


@dataclass(frozen=True)
class HistorianStreamBlock:
    sequence: int
    points: tuple[HistorianPoint, ...]


@dataclass(frozen=True)
class HistorianStreamTerminal:
    sequence: int
    block_count: int
    point_count: int


class HistorianStream(AbstractContextManager["HistorianStream"], Iterator[HistorianStreamBlock]):
    def __init__(self, transport: HistorianTransport, payload: dict[str, Any], max_block_rows: int):
        self._transport = transport
        self._payload = payload
        self._max_block_rows = max_block_rows
        self._context = None
        self._response = None
        self._lines = None
        self.header: HistorianStreamHeader | None = None
        self.terminal: HistorianStreamTerminal | None = None
        self._next_sequence = 0
        self._point_count = 0

    def __enter__(self) -> "HistorianStream":
        try:
            self._context = self._transport._client.stream(
                "POST", self._transport.base_url + self._transport.historian_stream_path,
                json=self._payload, headers={**self._transport._headers(), "Accept": "application/x-ndjson"},
                timeout=self._transport.timeout,
            )
            self._response = self._context.__enter__()
            self._response.raise_for_status()
        except httpx.TimeoutException as exc:
            self._close()
            raise HistorianStreamTransientError("Fluxy historian stream timed out") from exc
        except httpx.RequestError as exc:
            self._close()
            raise HistorianStreamTransientError("Fluxy historian stream transport failed") from exc
        except httpx.HTTPStatusError as exc:
            self._close()
            if exc.response.status_code == 429 or exc.response.status_code >= 500:
                raise HistorianStreamTransientError("Fluxy historian stream is temporarily unavailable") from exc
            raise HistorianStreamPermanentError("Fluxy historian stream request was rejected") from exc
        content_type = self._response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/x-ndjson":
            self._close()
            raise HistorianStreamProtocolError("Fluxy historian stream content type is not application/x-ndjson")
        self._lines = self._response.iter_lines()
        payload = self._next_payload("header")
        if set(payload) != {"type", "protocolVersion", "paths", "start", "end"} or payload.get("type") != "header" or payload.get("protocolVersion") != 1:
            self._close()
            raise HistorianStreamProtocolError("Fluxy historian stream has an invalid header")
        try:
            paths = tuple(HistorianPath(str(item["seriesKey"]), str(item["tagpath"])) for item in payload["paths"])
            self.header = HistorianStreamHeader(paths, int(payload["start"]), int(payload["end"]))
        except (KeyError, TypeError, ValueError) as exc:
            self._close()
            raise HistorianStreamProtocolError("Fluxy historian stream has an invalid header") from exc
        return self

    def __next__(self) -> HistorianStreamBlock:
        if self._lines is None or self.terminal is not None:
            raise StopIteration
        payload = self._next_payload("block or terminal")
        kind = payload.get("type")
        if kind == "terminal":
            self._parse_terminal(payload)
            raise StopIteration
        if kind != "block" or set(payload) != {"type", "sequence", "rowCount", "columns"}:
            raise HistorianStreamProtocolError("Fluxy historian stream has an invalid block")
        sequence = payload.get("sequence")
        row_count = payload.get("rowCount")
        columns = payload.get("columns")
        column_names = ("seriesKey", "tagpath", "timestamp", "value", "quality", "valueType")
        if type(sequence) is not int or sequence != self._next_sequence:
            raise HistorianStreamProtocolError("Fluxy historian stream block sequence is invalid")
        if type(row_count) is not int or row_count < 0 or row_count > self._max_block_rows:
            raise HistorianStreamProtocolError("Fluxy historian stream block exceeds its advertised bound")
        if not isinstance(columns, dict) or set(columns) != set(column_names) or any(
            not isinstance(columns[name], list) or len(columns[name]) != row_count for name in column_names
        ):
            raise HistorianStreamProtocolError("Fluxy historian stream block has invalid columns")
        try:
            points = tuple(_point_from_payload({name: columns[name][index] for name in column_names}) for index in range(row_count))
        except (KeyError, TypeError, ValueError) as exc:
            raise HistorianStreamProtocolError("Fluxy historian stream block contains an invalid point") from exc
        self._next_sequence += 1
        self._point_count += len(points)
        return HistorianStreamBlock(sequence, points)

    def _parse_terminal(self, payload: dict[str, Any]) -> None:
        allowed = {"type", "sequence", "ok", "blockCount", "pointCount"}
        if payload.get("ok") is False:
            if set(payload) != allowed | {"code", "error", "transient"} or not isinstance(payload.get("code"), str) or not isinstance(payload.get("error"), str) or type(payload.get("transient")) is not bool:
                raise HistorianStreamProtocolError("Fluxy historian stream has an invalid error terminal")
            self._validate_terminal_counts(payload)
            error_type = HistorianStreamTransientError if payload.get("transient") is True else HistorianStreamPermanentError
            raise error_type("Fluxy historian stream terminated with an error")
        if set(payload) != allowed or payload.get("ok") is not True:
            raise HistorianStreamProtocolError("Fluxy historian stream has an invalid terminal")
        sequence, blocks, points = self._validate_terminal_counts(payload)
        assert self._lines is not None
        try:
            next(self._lines)
        except StopIteration:
            pass
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise HistorianStreamTransientError("Fluxy historian stream transport failed") from exc
        else:
            raise HistorianStreamProtocolError("Fluxy historian stream contains records after its terminal")
        self.terminal = HistorianStreamTerminal(sequence, blocks, points)

    def _validate_terminal_counts(self, payload: dict[str, Any]) -> tuple[int, int, int]:
        sequence, blocks, points = payload.get("sequence"), payload.get("blockCount"), payload.get("pointCount")
        if type(sequence) is not int or type(blocks) is not int or type(points) is not int or sequence != self._next_sequence or blocks != self._next_sequence or points != self._point_count:
            raise HistorianStreamProtocolError("Fluxy historian stream terminal counts are inconsistent")
        return sequence, blocks, points

    def _next_payload(self, expected: str) -> dict[str, Any]:
        assert self._lines is not None
        try:
            line = next(self._lines)
        except StopIteration as exc:
            raise HistorianStreamProtocolError("Fluxy historian stream ended without a valid terminal") from exc
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise HistorianStreamTransientError("Fluxy historian stream transport failed") from exc
        if not line:
            raise HistorianStreamProtocolError("Fluxy historian stream contains an empty line")
        try:
            payload = json.loads(line)
        except (JSONDecodeError, UnicodeDecodeError) as exc:
            raise HistorianStreamProtocolError("Fluxy historian stream contains malformed JSON") from exc
        if not isinstance(payload, dict):
            raise HistorianStreamProtocolError("Fluxy historian stream records must be JSON objects")
        return payload

    def _close(self) -> None:
        if self._context is not None:
            self._context.__exit__(None, None, None)
            self._context = None

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._close()


@dataclass(frozen=True)
class HistorianAnnotation:
    storage_id: str
    path: str
    start_time: str | int | None = None
    end_time: str | int | None = None
    annotation_type: str | None = None
    data: str | None = None
    author: str | None = None
    payload: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "HistorianAnnotation":
        return cls(
            storage_id=str(payload.get("storageId") or ""),
            path=str(payload.get("path") or ""),
            start_time=payload.get("startTime"),
            end_time=payload.get("endTime"),
            annotation_type=payload.get("type"),
            data=payload.get("data"),
            author=payload.get("author"),
            payload=payload,
        )


@dataclass(frozen=True)
class HistorianMetadata:
    path: str
    timestamp: str | int | None = None
    properties: dict[str, Any] | None = None
    quality: str | None = None
    payload: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "HistorianMetadata":
        properties = payload.get("properties")
        return cls(
            path=str(payload.get("path") or ""),
            timestamp=payload.get("timestamp"),
            properties=properties if isinstance(properties, dict) else None,
            quality=payload.get("quality"),
            payload=payload,
        )


class HistorianClientMixin:
    def historian_browse(
        self: HistorianTransport,
        path: str,
        continuation_point: str | None = None,
    ) -> HistorianBrowsePage:
        payload = {"path": path}
        if continuation_point is not None:
            payload["continuationPoint"] = continuation_point
        response = self._post(self.historian_browse_path, payload)
        results = response.get("results")
        if not isinstance(results, list):
            from fluxy.client import FluxyError

            raise FluxyError("browse response missing `results` list")
        rows = [HistorianBrowseResult.from_payload(result) for result in results]
        return HistorianBrowsePage(rows, response.get("continuationPoint"), response.get("quality"))

    def capabilities(self: HistorianTransport) -> HistorianPageCapability:
        response = self._post(self.capabilities_path, {})
        capability = response.get("historianPage")
        if not isinstance(capability, dict):
            from fluxy.client import FluxyError

            raise FluxyError("capabilities response missing `historianPage` object")
        stream_payload = response.get("historianStream")
        stream = None
        if isinstance(stream_payload, dict):
            stream = HistorianStreamCapability(
                supported=bool(stream_payload.get("supported")),
                protocol_version=int(stream_payload.get("protocolVersion", 0)),
                max_block_rows=int(stream_payload.get("maxBlockRows", 0)),
                reason=stream_payload.get("reason"),
            )
        return HistorianPageCapability(
            supported=bool(capability.get("supported")),
            exact_raw_capture=bool(capability.get("exactRawCapture")),
            default_limit=int(capability.get("defaultLimit", 0)),
            max_limit=int(capability.get("maxLimit", 0)),
            equal_timestamp_paging=str(capability.get("equalTimestampPaging", "unsupported")),
            max_paths=int(capability.get("maxPaths", 0)),
            max_window_ms=int(capability.get("maxWindowMs", 0)),
            reason=capability.get("reason"),
            max_total_points=(
                int(capability["maxTotalPoints"])
                if capability.get("maxTotalPoints") is not None
                else None
            ),
            stream=stream,
        )

    def historian_stream(self: HistorianTransport, paths: list[HistorianPath], start: int, end: int, *, max_block_rows: int) -> HistorianStream:
        if max_block_rows < 1:
            raise ValueError("max_block_rows must be positive")
        payload = {"paths": [{"seriesKey": path.series_key, "tagpath": path.tagpath} for path in paths], "start": start, "end": end}
        return HistorianStream(self, payload, max_block_rows)

    def historian_page(
        self: HistorianTransport,
        paths: list[HistorianPath],
        start: int,
        end: int,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> HistorianPage:
        payload: dict[str, Any] = {
            "paths": [
                {"seriesKey": path.series_key, "tagpath": path.tagpath} for path in paths
            ],
            "start": start,
            "end": end,
        }
        if limit is not None:
            payload["limit"] = limit
        if cursor is not None:
            payload["cursor"] = cursor
        response = self._post(self.historian_page_path, payload)
        points = response.get("points")
        if not isinstance(points, list):
            from fluxy.client import FluxyError

            raise FluxyError("historian page response missing `points` list")
        return HistorianPage(
            paths=[
                HistorianPath(str(path["seriesKey"]), str(path["tagpath"]))
                for path in response["paths"]
            ],
            start=int(response["start"]),
            end=int(response["end"]),
            points=[
                HistorianPoint(
                    str(point["seriesKey"]),
                    str(point["tagpath"]),
                    int(point["timestamp"]),
                    point.get("value"),
                    str(point["quality"]),
                    str(point["valueType"]),
                )
                for point in points
            ],
            complete=bool(response.get("complete")),
            next_cursor=str(response["nextCursor"]) if response.get("nextCursor") is not None else None,
        )

    def historian_store_data_points(
        self: HistorianTransport,
        paths: list[str],
        values: list[Any],
        timestamps: list[int],
        qualities: list[int | str] | None = None,
    ) -> list[str]:
        payload: dict[str, Any] = {"paths": paths, "values": values, "timestamps": timestamps}
        if qualities is not None:
            payload["qualities"] = qualities
        response = self._post(self.historian_store_data_points_path, payload)
        return _quality_strings(response, "qualities", "storeDataPoints")

    def historian_query_raw_points(
        self: HistorianTransport,
        paths: list[str],
        start_time: int,
        end_time: int,
        return_size: int = 100,
    ) -> QueryResult:
        response = self._post(
            self.historian_query_raw_points_path,
            {
                "paths": paths,
                "startTime": start_time,
                "endTime": end_time,
                "returnSize": return_size,
            },
        )
        return query_result_from_response(response)

    def historian_query_aggregated_points(
        self: HistorianTransport,
        paths: list[str],
        start_time: int,
        end_time: int,
        aggregates: list[str] | None = None,
        fill_modes: list[str] | None = None,
        column_names: list[str] | None = None,
        return_format: str = "WIDE",
        return_size: int = 1,
        include_bounds: bool = False,
        exclude_observations: bool = False,
    ) -> QueryResult:
        payload: dict[str, Any] = {
            "paths": paths,
            "startTime": start_time,
            "endTime": end_time,
            "returnFormat": return_format,
            "returnSize": return_size,
            "includeBounds": include_bounds,
            "excludeObservations": exclude_observations,
        }
        optional = {
            "aggregates": aggregates,
            "fillModes": fill_modes,
            "columnNames": column_names,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})
        return query_result_from_response(
            self._post(self.historian_query_aggregated_points_path, payload)
        )

    def historian_store_annotations(
        self: HistorianTransport,
        paths: list[str],
        start_times: list[int],
        end_times: list[int] | None = None,
        types: list[str] | None = None,
        data: list[str] | None = None,
        storage_ids: list[str] | None = None,
        deleted: list[bool] | None = None,
    ) -> list[str]:
        payload: dict[str, Any] = {"paths": paths, "startTimes": start_times}
        optional = {
            "endTimes": end_times,
            "types": types,
            "data": data,
            "storageIds": storage_ids,
            "deleted": deleted,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})
        response = self._post(self.historian_store_annotations_path, payload)
        return _quality_strings(response, "qualities", "storeAnnotations")

    def historian_query_annotations(
        self: HistorianTransport,
        paths: list[str],
        start_date: int,
        end_date: int | None = None,
        allowed_types: list[str] | None = None,
    ) -> list[HistorianAnnotation]:
        payload: dict[str, Any] = {"paths": paths, "startDate": start_date}
        if end_date is not None:
            payload["endDate"] = end_date
        if allowed_types is not None:
            payload["allowedTypes"] = allowed_types
        response = self._post(self.historian_query_annotations_path, payload)
        annotations = response.get("annotations")
        if not isinstance(annotations, list):
            from fluxy.client import FluxyError

            raise FluxyError("queryAnnotations response missing `annotations` list")
        return [HistorianAnnotation.from_payload(annotation) for annotation in annotations]

    def historian_delete_annotations(
        self: HistorianTransport,
        paths: list[str],
        storage_ids: list[str],
    ) -> list[str]:
        response = self._post(
            self.historian_delete_annotations_path,
            {"paths": paths, "storageIds": storage_ids},
        )
        return _quality_strings(response, "qualities", "deleteAnnotations")

    def historian_store_metadata(
        self: HistorianTransport,
        paths: list[str],
        timestamps: list[int],
        properties: dict[str, Any],
    ) -> list[str]:
        response = self._post(
            self.historian_store_metadata_path,
            {"paths": paths, "timestamps": timestamps, "properties": properties},
        )
        return _quality_strings(response, "qualities", "storeMetadata")

    def historian_query_metadata(
        self: HistorianTransport,
        paths: list[str],
        start_date: int | None = None,
        end_date: int | None = None,
    ) -> list[HistorianMetadata]:
        payload: dict[str, Any] = {"paths": paths}
        if start_date is not None:
            payload["startDate"] = start_date
        if end_date is not None:
            payload["endDate"] = end_date
        response = self._post(self.historian_query_metadata_path, payload)
        metadata = response.get("metadata")
        if not isinstance(metadata, list):
            from fluxy.client import FluxyError

            raise FluxyError("queryMetadata response missing `metadata` list")
        return [HistorianMetadata.from_payload(row) for row in metadata]


def _quality_strings(response: dict[str, Any], key: str, operation: str) -> list[str]:
    qualities = response.get(key)
    if not isinstance(qualities, list):
        from fluxy.client import FluxyError

        raise FluxyError("%s response missing `%s` list" % (operation, key))
    return [str(quality) for quality in qualities]


def _point_from_payload(point: dict[str, Any]) -> HistorianPoint:
    if not isinstance(point, dict) or set(point) != {"seriesKey", "tagpath", "timestamp", "value", "quality", "valueType"}:
        raise ValueError("invalid point")
    return HistorianPoint(str(point["seriesKey"]), str(point["tagpath"]), int(point["timestamp"]), point["value"], str(point["quality"]), str(point["valueType"]))
