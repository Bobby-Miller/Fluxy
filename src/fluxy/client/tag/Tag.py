from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, overload


@dataclass(frozen=True)
class QualifiedValue:
    value: Any
    quality: str
    timestamp: Any = None
    tag_path: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "QualifiedValue":
        return cls(
            value=payload.get("value"),
            quality=str(payload.get("quality", "Unknown")),
            timestamp=payload.get("timestamp"),
            tag_path=payload.get("tagPath") or payload.get("tag_path"),
        )


@dataclass(frozen=True)
class WriteResult:
    quality: str
    tag_path: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "WriteResult":
        return cls(
            quality=str(payload.get("quality", "Unknown")),
            tag_path=payload.get("tagPath") or payload.get("tag_path"),
        )


@dataclass(frozen=True)
class DeleteResult:
    quality: str
    tag_path: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DeleteResult":
        return cls(
            quality=str(payload.get("quality", "Unknown")),
            tag_path=payload.get("tagPath") or payload.get("tag_path"),
        )


@dataclass(frozen=True)
class CopyResult:
    quality: str
    tag_path: str | None = None
    destination_path: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "CopyResult":
        return cls(
            quality=str(payload.get("quality", "Unknown")),
            tag_path=payload.get("tagPath") or payload.get("tag_path"),
            destination_path=payload.get("destinationPath") or payload.get("destination_path"),
        )


@dataclass(frozen=True)
class MoveResult:
    quality: str
    source_path: str | None = None
    destination_path: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MoveResult":
        return cls(
            quality=str(payload.get("quality", "Unknown")),
            source_path=payload.get("sourcePath") or payload.get("source_path"),
            destination_path=payload.get("destinationPath") or payload.get("destination_path"),
        )


@dataclass(frozen=True)
class RenameResult:
    quality: str
    tag_path: str | None = None
    new_name: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RenameResult":
        return cls(
            quality=str(payload.get("quality", "Unknown")),
            tag_path=payload.get("tagPath") or payload.get("tag_path"),
            new_name=payload.get("newName") or payload.get("new_name"),
        )


@dataclass(frozen=True)
class ImportResult:
    quality: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ImportResult":
        return cls(quality=str(payload.get("quality", "Unknown")))


@dataclass(frozen=True)
class ExportTagsResult:
    tags: Any
    raw_json: str


@dataclass(frozen=True)
class ConfigureResult:
    quality: str
    name: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ConfigureResult":
        return cls(
            quality=str(payload.get("quality", "Unknown")),
            name=payload.get("name"),
        )


@dataclass(frozen=True)
class BrowseResult:
    name: str | None = None
    full_path: str | None = None
    tag_type: str | None = None
    data_type: str | None = None
    has_children: bool | None = None
    payload: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "BrowseResult":
        return cls(
            name=payload.get("name"),
            full_path=payload.get("fullPath") or payload.get("full_path"),
            tag_type=payload.get("tagType") or payload.get("tag_type"),
            data_type=payload.get("dataType") or payload.get("data_type"),
            has_children=payload.get("hasChildren") or payload.get("has_children"),
            payload=payload,
        )


class TagQueryResult(list[dict[str, Any]]):
    def __init__(self, rows: list[dict[str, Any]], continuation_point: str | None = None) -> None:
        super().__init__(rows)
        self.continuation_point = continuation_point


class TagTransport(Protocol):
    read_path: str
    write_path: str
    delete_path: str
    copy_path: str
    move_path: str
    rename_path: str
    import_path: str
    export_path: str
    get_configuration_path: str
    configure_path: str
    browse_path: str
    query_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def browse(
        self,
        path: str,
        tag_filter: dict[str, Any] | None = None,
    ) -> list[BrowseResult]: ...


class TagClientMixin:
    @overload
    def read_blocking(
        self: TagTransport, tag_paths: str, timeout_ms: int | None = None
    ) -> QualifiedValue: ...

    @overload
    def read_blocking(
        self: TagTransport, tag_paths: list[str], timeout_ms: int | None = None
    ) -> list[QualifiedValue]: ...

    def read_blocking(
        self: TagTransport, tag_paths: str | list[str], timeout_ms: int | None = None
    ) -> QualifiedValue | list[QualifiedValue]:
        single = isinstance(tag_paths, str)
        normalized_paths = [tag_paths] if single else tag_paths
        payload: dict[str, Any] = {"tagPaths": normalized_paths}
        if timeout_ms is not None:
            payload["timeoutMs"] = timeout_ms
        response = self._post(self.read_path, payload)
        values = response.get("values")
        if not isinstance(values, list):
            from fluxy.client import FluxyError

            raise FluxyError("readBlocking response missing `values` list")
        qualified_values = [QualifiedValue.from_payload(value) for value in values]
        return qualified_values[0] if single else qualified_values

    @overload
    def write_blocking(
        self: TagTransport,
        tag_paths: str,
        values: Any,
        timeout_ms: int | None = None,
    ) -> WriteResult: ...

    @overload
    def write_blocking(
        self: TagTransport,
        tag_paths: list[str],
        values: list[Any],
        timeout_ms: int | None = None,
    ) -> list[WriteResult]: ...

    def write_blocking(
        self: TagTransport,
        tag_paths: str | list[str],
        values: Any | list[Any],
        timeout_ms: int | None = None,
    ) -> WriteResult | list[WriteResult]:
        single = isinstance(tag_paths, str)
        normalized_paths = [tag_paths] if single else tag_paths
        normalized_values = [values] if single else values
        if not isinstance(normalized_values, list):
            raise ValueError("values must be a list when tag_paths is a list")
        if len(normalized_paths) != len(normalized_values):
            raise ValueError("tag_paths and values must be the same length")

        payload: dict[str, Any] = {"tagPaths": normalized_paths, "values": normalized_values}
        if timeout_ms is not None:
            payload["timeoutMs"] = timeout_ms
        response = self._post(self.write_path, payload)
        qualities = response.get("qualities")
        if not isinstance(qualities, list):
            from fluxy.client import FluxyError

            raise FluxyError("writeBlocking response missing `qualities` list")
        write_results = [WriteResult.from_payload(quality) for quality in qualities]
        return write_results[0] if single else write_results

    @overload
    def delete_tags(self: TagTransport, tag_paths: str) -> DeleteResult: ...

    @overload
    def delete_tags(self: TagTransport, tag_paths: list[str]) -> list[DeleteResult]: ...

    def delete_tags(self: TagTransport, tag_paths: str | list[str]) -> DeleteResult | list[DeleteResult]:
        single = isinstance(tag_paths, str)
        normalized_paths = [tag_paths] if single else tag_paths
        response = self._post(self.delete_path, {"tagPaths": normalized_paths})
        qualities = response.get("qualities")
        if not isinstance(qualities, list):
            from fluxy.client import FluxyError

            raise FluxyError("deleteTags response missing `qualities` list")
        delete_results = [DeleteResult.from_payload(quality) for quality in qualities]
        return delete_results[0] if single else delete_results

    @overload
    def copy(
        self: TagTransport,
        tag_paths: str,
        destination_path: str,
        collision_policy: str = "o",
    ) -> CopyResult: ...

    @overload
    def copy(
        self: TagTransport,
        tag_paths: list[str],
        destination_path: str,
        collision_policy: str = "o",
    ) -> list[CopyResult]: ...

    def copy(
        self: TagTransport,
        tag_paths: str | list[str],
        destination_path: str,
        collision_policy: str = "o",
    ) -> CopyResult | list[CopyResult]:
        single = isinstance(tag_paths, str)
        normalized_paths = [tag_paths] if single else tag_paths
        response = self._post(
            self.copy_path,
            {"tagPaths": normalized_paths, "destinationPath": destination_path, "collisionPolicy": collision_policy},
        )
        qualities = response.get("qualities")
        if not isinstance(qualities, list):
            from fluxy.client import FluxyError

            raise FluxyError("copy response missing `qualities` list")
        copy_results = [CopyResult.from_payload(quality) for quality in qualities]
        return copy_results[0] if single else copy_results

    def move(self: TagTransport, source_path: str, destination_path: str) -> MoveResult:
        response = self._post(
            self.move_path,
            {"sourcePath": source_path, "destinationPath": destination_path},
        )
        quality = response.get("quality")
        if not isinstance(quality, dict):
            from fluxy.client import FluxyError

            raise FluxyError("move response missing `quality` object")
        return MoveResult.from_payload(quality)

    def rename(self: TagTransport, tag_path: str, new_name: str) -> RenameResult:
        response = self._post(self.rename_path, {"tagPath": tag_path, "newName": new_name})
        quality = response.get("quality")
        if not isinstance(quality, dict):
            from fluxy.client import FluxyError

            raise FluxyError("rename response missing `quality` object")
        return RenameResult.from_payload(quality)

    def import_tags(
        self: TagTransport,
        tags: Any,
        base_path: str,
        collision_policy: str = "o",
    ) -> list[ImportResult]:
        payload = {
            "tags": tags,
            "basePath": base_path,
            "collisionPolicy": collision_policy,
        }
        response = self._post(self.import_path, payload)
        qualities = response.get("qualities")
        if not isinstance(qualities, list):
            from fluxy.client import FluxyError

            raise FluxyError("importTags response missing `qualities` list")
        return [ImportResult.from_payload(quality) for quality in qualities]

    def export_tags(self: TagTransport, tag_paths: str | list[str], recursive: bool = True) -> ExportTagsResult:
        normalized_paths = [tag_paths] if isinstance(tag_paths, str) else tag_paths
        response = self._post(self.export_path, {"tagPaths": normalized_paths, "recursive": recursive})
        if "tags" not in response or not isinstance(response.get("rawJson"), str):
            from fluxy.client import FluxyError

            raise FluxyError("exportTags response missing `tags` or `rawJson`")
        return ExportTagsResult(tags=response["tags"], raw_json=response["rawJson"])

    def get_configuration(
        self: TagTransport, path: str | list[str], recursive: bool = False
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"recursive": recursive}
        if isinstance(path, list):
            payload["paths"] = path
        else:
            payload["path"] = path
        response = self._post(self.get_configuration_path, payload)
        configs = response.get("configs")
        if not isinstance(configs, list):
            from fluxy.client import FluxyError

            raise FluxyError("getConfiguration response missing `configs` list")
        return configs

    def configure(
        self: TagTransport,
        base_path: str,
        tags: list[dict[str, Any]],
        collision_policy: str = "o",
    ) -> list[ConfigureResult]:
        payload = {
            "basePath": base_path,
            "tags": tags,
            "collisionPolicy": collision_policy,
        }
        response = self._post(self.configure_path, payload)
        qualities = response.get("qualities")
        if not isinstance(qualities, list):
            from fluxy.client import FluxyError

            raise FluxyError("configure response missing `qualities` list")
        return [ConfigureResult.from_payload(quality) for quality in qualities]

    def browse(
        self: TagTransport,
        path: str,
        tag_filter: dict[str, Any] | None = None,
    ) -> list[BrowseResult]:
        payload: dict[str, Any] = {"path": path}
        if tag_filter is not None:
            payload["filter"] = tag_filter
        response = self._post(self.browse_path, payload)
        results = response.get("results")
        if not isinstance(results, list):
            from fluxy.client import FluxyError

            raise FluxyError("browse response missing `results` list")
        return [BrowseResult.from_payload(result) for result in results]

    def list_paths(
        self: TagTransport,
        path: str,
        tag_filter: dict[str, Any] | None = None,
    ) -> list[str]:
        return [result.full_path for result in self.browse(path, tag_filter=tag_filter) if result.full_path]

    def query(
        self: TagTransport,
        provider: str,
        query: dict[str, Any] | None = None,
        limit: int | None = None,
        continuation: str | None = None,
    ) -> TagQueryResult:
        payload: dict[str, Any] = {"provider": provider}
        if query is not None:
            payload["query"] = query
        if limit is not None:
            payload["limit"] = limit
        if continuation is not None:
            payload["continuation"] = continuation
        response = self._post(self.query_path, payload)
        results = response.get("results")
        if not isinstance(results, list):
            from fluxy.client import FluxyError

            raise FluxyError("query response missing `results` list")
        rows = [dict(result) for result in results if isinstance(result, dict)]
        return TagQueryResult(rows, continuation_point=response.get("continuationPoint"))
