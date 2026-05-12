from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class DeviceConnection:
    name: str
    enabled: bool | None = None
    state: str | None = None
    driver: str | None = None
    payload: dict[str, Any] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DeviceConnection":
        name = payload.get("name") or payload.get("Name") or ""
        enabled = payload.get("enabled")
        if enabled is None:
            enabled = payload.get("Enabled")
        return cls(
            name=str(name),
            enabled=enabled if isinstance(enabled, bool) else None,
            state=payload.get("state") or payload.get("State"),
            driver=payload.get("driver") or payload.get("Driver"),
            payload=payload,
        )


class DeviceTransport(Protocol):
    device_list_devices_path: str
    device_add_device_path: str
    device_remove_device_path: str
    device_set_device_enabled_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class DeviceClientMixin:
    def device_list_devices(self: DeviceTransport) -> list[DeviceConnection]:
        response = self._post(self.device_list_devices_path, {})
        devices = response.get("devices")
        if not isinstance(devices, list):
            from fluxy.client import FluxyError

            raise FluxyError("listDevices response missing `devices` list")
        return [DeviceConnection.from_payload(device) for device in devices]

    def device_add_device(
        self: DeviceTransport,
        device_type: str,
        device_name: str,
        device_props: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> bool:
        payload: dict[str, Any] = {
            "deviceType": device_type,
            "deviceName": device_name,
            "deviceProps": device_props or {},
        }
        if description is not None:
            payload["description"] = description
        response = self._post(self.device_add_device_path, payload)
        return bool(response.get("ok"))

    def device_remove_device(self: DeviceTransport, device_name: str) -> bool:
        response = self._post(self.device_remove_device_path, {"deviceName": device_name})
        return bool(response.get("ok"))

    def device_set_device_enabled(self: DeviceTransport, device_name: str, enabled: bool) -> bool:
        response = self._post(
            self.device_set_device_enabled_path,
            {"deviceName": device_name, "enabled": enabled},
        )
        return bool(response.get("ok"))
