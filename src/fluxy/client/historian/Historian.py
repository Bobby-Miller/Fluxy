from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from fluxy.client.db import QueryResult
from fluxy.client.db.DB import query_result_from_response


class HistorianTransport(Protocol):
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
    ) -> list[HistorianBrowseResult]:
        payload = {"path": path}
        if continuation_point is not None:
            payload["continuationPoint"] = continuation_point
        response = self._post(self.historian_browse_path, payload)
        results = response.get("results")
        if not isinstance(results, list):
            from fluxy.client import FluxyError

            raise FluxyError("browse response missing `results` list")
        return [HistorianBrowseResult.from_payload(result) for result in results]

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
