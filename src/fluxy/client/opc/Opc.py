from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class OpcValue:
    value: Any
    quality: str
    timestamp: int | None = None


class OpcTransport(Protocol):
    opc_get_servers_path: str
    opc_get_server_state_path: str
    opc_browse_path: str
    opc_browse_server_path: str
    opc_browse_simple_path: str
    opc_read_value_path: str
    opc_read_values_path: str
    opc_write_value_path: str
    opc_write_values_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class OpcClientMixin:
    def opc_get_servers(self: OpcTransport, include_disabled: bool = False) -> list[str]:
        response = self._post(self.opc_get_servers_path, {"includeDisabled": include_disabled})
        servers = response.get("servers")
        if not isinstance(servers, list):
            from fluxy.client import FluxyError

            raise FluxyError("getServers response missing `servers` list")
        return [str(server) for server in servers]

    def opc_get_server_state(self: OpcTransport, opc_server: str) -> str | None:
        response = self._post(self.opc_get_server_state_path, {"opcServer": opc_server})
        state = response.get("state")
        return str(state) if state is not None else None

    def opc_browse(
        self: OpcTransport,
        opc_server: str | None = None,
        device: str | None = None,
        folder_path: str | None = None,
        opc_item_path: str | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {}
        if opc_server is not None:
            payload["opcServer"] = opc_server
        if device is not None:
            payload["device"] = device
        if folder_path is not None:
            payload["folderPath"] = folder_path
        if opc_item_path is not None:
            payload["opcItemPath"] = opc_item_path
        response = self._post(self.opc_browse_path, payload)
        results = response.get("results")
        if not isinstance(results, list):
            from fluxy.client import FluxyError

            raise FluxyError("browse response missing `results` list")
        return [dict(result) for result in results if isinstance(result, dict)]

    def opc_browse_server(
        self: OpcTransport, opc_server: str, node_id: str
    ) -> list[dict[str, Any]]:
        response = self._post(
            self.opc_browse_server_path, {"opcServer": opc_server, "nodeId": node_id}
        )
        results = response.get("results")
        if not isinstance(results, list):
            from fluxy.client import FluxyError

            raise FluxyError("browseServer response missing `results` list")
        return [dict(result) for result in results if isinstance(result, dict)]

    def opc_browse_simple(
        self: OpcTransport,
        opc_server: str | None = None,
        device: str | None = None,
        folder_path: str | None = None,
        opc_item_path: str | None = None,
    ) -> list[dict[str, Any]]:
        response = self._post(
            self.opc_browse_simple_path,
            {
                "opcServer": opc_server,
                "device": device,
                "folderPath": folder_path,
                "opcItemPath": opc_item_path,
            },
        )
        results = response.get("results")
        if not isinstance(results, list):
            from fluxy.client import FluxyError

            raise FluxyError("browseSimple response missing `results` list")
        return [dict(result) for result in results if isinstance(result, dict)]

    def opc_read_value(self: OpcTransport, opc_server: str, item_path: str) -> OpcValue:
        response = self._post(
            self.opc_read_value_path, {"opcServer": opc_server, "itemPath": item_path}
        )
        return OpcValue(
            value=response.get("value"),
            quality=str(response.get("quality") or ""),
            timestamp=response.get("timestamp")
            if isinstance(response.get("timestamp"), int)
            else None,
        )

    def opc_read_values(
        self: OpcTransport, opc_server: str, item_paths: list[str]
    ) -> list[OpcValue]:
        response = self._post(
            self.opc_read_values_path, {"opcServer": opc_server, "itemPaths": item_paths}
        )
        values = response.get("values")
        if not isinstance(values, list):
            from fluxy.client import FluxyError

            raise FluxyError("readValues response missing `values` list")
        return [
            OpcValue(
                value=item.get("value"),
                quality=str(item.get("quality") or ""),
                timestamp=item.get("timestamp") if isinstance(item.get("timestamp"), int) else None,
            )
            for item in values
            if isinstance(item, dict)
        ]

    def opc_write_value(self: OpcTransport, opc_server: str, item_path: str, value: Any) -> str:
        response = self._post(
            self.opc_write_value_path,
            {"opcServer": opc_server, "itemPath": item_path, "value": value},
        )
        return str(response.get("quality") or "")

    def opc_write_values(
        self: OpcTransport, opc_server: str, item_paths: list[str], values: list[Any]
    ) -> list[str]:
        response = self._post(
            self.opc_write_values_path,
            {"opcServer": opc_server, "itemPaths": item_paths, "values": values},
        )
        qualities = response.get("qualities")
        if not isinstance(qualities, list):
            from fluxy.client import FluxyError

            raise FluxyError("writeValues response missing `qualities` list")
        return [str(quality) for quality in qualities]
