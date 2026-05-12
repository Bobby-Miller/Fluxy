from __future__ import annotations

from typing import Any, Protocol


class OpcUaTransport(Protocol):
    opcua_add_connection_path: str
    opcua_remove_connection_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class OpcUaClientMixin:
    def opcua_add_connection(
        self: OpcUaTransport,
        name: str,
        description: str,
        discovery_url: str,
        endpoint_url: str,
        security_policy: str = "None",
        security_mode: str = "None",
        settings: dict[str, Any] | None = None,
    ) -> bool:
        response = self._post(
            self.opcua_add_connection_path,
            {
                "name": name,
                "description": description,
                "discoveryUrl": discovery_url,
                "endpointUrl": endpoint_url,
                "securityPolicy": security_policy,
                "securityMode": security_mode,
                "settings": settings or {},
            },
        )
        return bool(response.get("ok"))

    def opcua_remove_connection(self: OpcUaTransport, name: str) -> bool:
        response = self._post(self.opcua_remove_connection_path, {"name": name})
        return bool(response.get("ok"))
