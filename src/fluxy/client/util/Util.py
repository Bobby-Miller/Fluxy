from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from fluxy.client.db import QueryResult
from fluxy.client.db.DB import query_result_from_response


@dataclass(frozen=True)
class IgnitionVersion:
    version: str
    major: int | None = None
    minor: int | None = None


class UtilTransport(Protocol):
    util_get_version_path: str
    _ignition_version_cache: IgnitionVersion | None
    util_get_modules_path: str
    util_get_gateway_status_path: str
    util_get_project_name_path: str
    util_audit_path: str
    util_query_audit_log_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class UtilClientMixin:
    def util_get_version(self: UtilTransport, *, refresh: bool = False) -> IgnitionVersion:
        if self._ignition_version_cache is not None and not refresh:
            return self._ignition_version_cache
        response = self._post(self.util_get_version_path, {})
        major = response.get("major")
        minor = response.get("minor")
        version = IgnitionVersion(
            version=str(response.get("version") or ""),
            major=major if isinstance(major, int) else None,
            minor=minor if isinstance(minor, int) else None,
        )
        self._ignition_version_cache = version
        return version

    def util_get_modules(self: UtilTransport) -> QueryResult:
        return query_result_from_response(self._post(self.util_get_modules_path, {}))

    def util_get_gateway_status(
        self: UtilTransport,
        gateway_address: str,
        connect_timeout_millis: int | None = None,
        socket_timeout_millis: int | None = None,
        bypass_cert_validation: bool | None = None,
    ) -> str:
        payload: dict[str, Any] = {"gatewayAddress": gateway_address}
        if connect_timeout_millis is not None:
            payload["connectTimeoutMillis"] = connect_timeout_millis
        if socket_timeout_millis is not None:
            payload["socketTimeoutMillis"] = socket_timeout_millis
        if bypass_cert_validation is not None:
            payload["bypassCertValidation"] = bypass_cert_validation
        response = self._post(self.util_get_gateway_status_path, payload)
        return str(response.get("status") or "")

    def util_get_project_name(self: UtilTransport) -> str:
        response = self._post(self.util_get_project_name_path, {})
        return str(response.get("projectName") or "")

    def util_audit(
        self: UtilTransport,
        action: str,
        action_target: str | None = None,
        action_value: str | None = None,
        audit_profile: str | None = None,
        actor: str | None = None,
        actor_host: str | None = None,
        originating_system: list[str] | str | None = None,
        event_timestamp: int | None = None,
        originating_context: int | None = None,
        status_code: int | None = None,
    ) -> bool:
        payload: dict[str, Any] = {"action": action}
        optional = {
            "actionTarget": action_target,
            "actionValue": action_value,
            "auditProfile": audit_profile,
            "actor": actor,
            "actorHost": actor_host,
            "originatingSystem": originating_system,
            "eventTimestamp": event_timestamp,
            "originatingContext": originating_context,
            "statusCode": status_code,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})
        response = self._post(self.util_audit_path, payload)
        return bool(response.get("ok"))

    def util_query_audit_log(
        self: UtilTransport,
        audit_profile_name: str,
        start_date: int | None = None,
        end_date: int | None = None,
        actor_filter: str | None = None,
        action_filter: str | None = None,
        target_filter: str | None = None,
        value_filter: str | None = None,
        system_filter: str | None = None,
        context_filter: int | None = None,
    ) -> QueryResult:
        payload: dict[str, Any] = {"auditProfileName": audit_profile_name}
        optional = {
            "startDate": start_date,
            "endDate": end_date,
            "actorFilter": actor_filter,
            "actionFilter": action_filter,
            "targetFilter": target_filter,
            "valueFilter": value_filter,
            "systemFilter": system_filter,
            "contextFilter": context_filter,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})
        return query_result_from_response(self._post(self.util_query_audit_log_path, payload))
