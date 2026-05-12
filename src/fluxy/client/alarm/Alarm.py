from __future__ import annotations

from typing import Any, Protocol

from fluxy.client.db import QueryResult
from fluxy.client.db.DB import query_result_from_response


class AlarmTransport(Protocol):
    alarm_query_status_path: str
    alarm_shelve_path: str
    alarm_unshelve_path: str
    alarm_get_shelved_paths_path: str
    alarm_acknowledge_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class AlarmClientMixin:
    def alarm_query_status(
        self: AlarmTransport,
        priority: list[int | str] | None = None,
        state: list[int | str] | None = None,
        source: list[str] | None = None,
        include_shelved: bool = False,
        provider: list[str] | None = None,
    ) -> QueryResult:
        payload: dict[str, Any] = {"includeShelved": include_shelved}
        if priority is not None:
            payload["priority"] = priority
        if state is not None:
            payload["state"] = state
        if source is not None:
            payload["source"] = source
        if provider is not None:
            payload["provider"] = provider
        return query_result_from_response(self._post(self.alarm_query_status_path, payload))

    def alarm_shelve(
        self: AlarmTransport,
        paths: list[str],
        timeout_seconds: int | None = None,
        timeout_minutes: int | None = None,
    ) -> bool:
        payload: dict[str, Any] = {"paths": paths}
        if timeout_seconds is not None:
            payload["timeoutSeconds"] = timeout_seconds
        if timeout_minutes is not None:
            payload["timeoutMinutes"] = timeout_minutes
        response = self._post(self.alarm_shelve_path, payload)
        return bool(response.get("ok"))

    def alarm_unshelve(self: AlarmTransport, paths: list[str]) -> bool:
        response = self._post(self.alarm_unshelve_path, {"paths": paths})
        return bool(response.get("ok"))

    def alarm_get_shelved_paths(self: AlarmTransport) -> list[dict[str, Any]]:
        response = self._post(self.alarm_get_shelved_paths_path, {})
        results = response.get("results")
        if not isinstance(results, list):
            from fluxy.client import FluxyError

            raise FluxyError("getShelvedPaths response missing `results` list")
        return [dict(result) for result in results if isinstance(result, dict)]

    def alarm_acknowledge(
        self: AlarmTransport, alarm_ids: list[str], notes: str | None = None, username: str = "fluxy"
    ) -> list[str]:
        payload: dict[str, Any] = {"alarmIds": alarm_ids, "username": username}
        if notes is not None:
            payload["notes"] = notes
        response = self._post(self.alarm_acknowledge_path, payload)
        failed = response.get("failed")
        if not isinstance(failed, list):
            from fluxy.client import FluxyError

            raise FluxyError("acknowledge response missing `failed` list")
        return [str(alarm_id) for alarm_id in failed]
