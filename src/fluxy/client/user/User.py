from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class UserTransport(Protocol):
    user_get_user_sources_path: str
    user_get_roles_path: str
    user_add_role_path: str
    user_edit_role_path: str
    user_remove_role_path: str
    user_add_user_path: str
    user_get_user_path: str
    user_get_users_path: str
    user_edit_user_path: str
    user_remove_user_path: str
    user_add_schedule_path: str
    user_get_schedule_path: str
    user_get_schedules_path: str
    user_remove_schedule_path: str
    user_add_holiday_path: str
    user_get_holiday_path: str
    user_get_holidays_path: str
    user_remove_holiday_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class UserResponse:
    warnings: list[str]
    errors: list[str]
    infos: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "UserResponse":
        return cls(
            warnings=[str(value) for value in payload.get("warnings") or []],
            errors=[str(value) for value in payload.get("errors") or []],
            infos=[str(value) for value in payload.get("infos") or []],
        )


class UserClientMixin:
    def user_get_user_sources(self: UserTransport) -> list[dict[str, Any]]:
        response = self._post(self.user_get_user_sources_path, {})
        sources = response.get("sources")
        if not isinstance(sources, list):
            from fluxy.client import FluxyError

            raise FluxyError("getUserSources response missing `sources` list")
        return [dict(source) for source in sources]

    def user_get_roles(self: UserTransport, user_source: str) -> list[str]:
        response = self._post(self.user_get_roles_path, {"userSource": user_source})
        return _strings_response(response, "roles", "getRoles")

    def user_add_role(self: UserTransport, user_source: str, role: str) -> UserResponse:
        return UserResponse.from_payload(
            self._post(self.user_add_role_path, {"userSource": user_source, "role": role})
        )

    def user_edit_role(
        self: UserTransport, user_source: str, old_name: str, new_name: str
    ) -> UserResponse:
        return UserResponse.from_payload(
            self._post(
                self.user_edit_role_path,
                {"userSource": user_source, "oldName": old_name, "newName": new_name},
            )
        )

    def user_remove_role(self: UserTransport, user_source: str, role: str) -> UserResponse:
        return UserResponse.from_payload(
            self._post(self.user_remove_role_path, {"userSource": user_source, "role": role})
        )

    def user_add_user(
        self: UserTransport,
        user_source: str,
        username: str,
        password: str,
        fields: dict[str, Any] | None = None,
        roles: list[str] | None = None,
        contact_info: dict[str, str] | None = None,
    ) -> UserResponse:
        return UserResponse.from_payload(
            self._post(
                self.user_add_user_path,
                {
                    "userSource": user_source,
                    "username": username,
                    "password": password,
                    "fields": fields or {},
                    "roles": roles or [],
                    "contactInfo": contact_info or {},
                },
            )
        )

    def user_get_user(self: UserTransport, user_source: str, username: str) -> dict[str, Any]:
        response = self._post(
            self.user_get_user_path,
            {"userSource": user_source, "username": username},
        )
        user = response.get("user")
        if not isinstance(user, dict):
            from fluxy.client import FluxyError

            raise FluxyError("getUser response missing `user` object")
        return dict(user)

    def user_get_users(self: UserTransport, user_source: str) -> list[dict[str, Any]]:
        response = self._post(self.user_get_users_path, {"userSource": user_source})
        users = response.get("users")
        if not isinstance(users, list):
            from fluxy.client import FluxyError

            raise FluxyError("getUsers response missing `users` list")
        return [dict(user) for user in users]

    def user_edit_user(
        self: UserTransport,
        user_source: str,
        username: str,
        fields: dict[str, Any] | None = None,
        roles: list[str] | None = None,
        contact_info: dict[str, str] | None = None,
        password: str | None = None,
    ) -> UserResponse:
        payload: dict[str, Any] = {
            "userSource": user_source,
            "username": username,
            "fields": fields or {},
            "roles": roles or [],
            "contactInfo": contact_info or {},
        }
        if password is not None:
            payload["password"] = password
        return UserResponse.from_payload(self._post(self.user_edit_user_path, payload))

    def user_remove_user(self: UserTransport, user_source: str, username: str) -> UserResponse:
        return UserResponse.from_payload(
            self._post(self.user_remove_user_path, {"userSource": user_source, "username": username})
        )

    def user_add_schedule(
        self: UserTransport,
        name: str,
        source_schedule: str = "Always",
        description: str | None = None,
    ) -> UserResponse:
        payload: dict[str, Any] = {"name": name, "sourceSchedule": source_schedule}
        if description is not None:
            payload["description"] = description
        return UserResponse.from_payload(self._post(self.user_add_schedule_path, payload))

    def user_get_schedule(self: UserTransport, name: str) -> dict[str, Any]:
        return _object_response(self._post(self.user_get_schedule_path, {"name": name}), "schedule")

    def user_get_schedules(self: UserTransport) -> list[dict[str, Any]]:
        response = self._post(self.user_get_schedules_path, {})
        schedules = response.get("schedules")
        if not isinstance(schedules, list):
            from fluxy.client import FluxyError

            raise FluxyError("getSchedules response missing `schedules` list")
        return [dict(schedule) for schedule in schedules]

    def user_remove_schedule(self: UserTransport, name: str) -> UserResponse:
        return UserResponse.from_payload(self._post(self.user_remove_schedule_path, {"name": name}))

    def user_add_holiday(
        self: UserTransport,
        name: str,
        date: int,
        repeat_annually: bool = False,
    ) -> UserResponse:
        return UserResponse.from_payload(
            self._post(
                self.user_add_holiday_path,
                {"name": name, "date": date, "repeatAnnually": repeat_annually},
            )
        )

    def user_get_holiday(self: UserTransport, name: str) -> dict[str, Any]:
        return _object_response(self._post(self.user_get_holiday_path, {"name": name}), "holiday")

    def user_get_holidays(self: UserTransport) -> list[dict[str, Any]]:
        response = self._post(self.user_get_holidays_path, {})
        holidays = response.get("holidays")
        if not isinstance(holidays, list):
            from fluxy.client import FluxyError

            raise FluxyError("getHolidays response missing `holidays` list")
        return [dict(holiday) for holiday in holidays]

    def user_remove_holiday(self: UserTransport, name: str) -> UserResponse:
        return UserResponse.from_payload(self._post(self.user_remove_holiday_path, {"name": name}))


def _strings_response(response: dict[str, Any], key: str, operation: str) -> list[str]:
    values = response.get(key)
    if not isinstance(values, list):
        from fluxy.client import FluxyError

        raise FluxyError("%s response missing `%s` list" % (operation, key))
    return [str(value) for value in values]


def _object_response(response: dict[str, Any], key: str) -> dict[str, Any]:
    value = response.get(key)
    if not isinstance(value, dict):
        from fluxy.client import FluxyError

        raise FluxyError("response missing `%s` object" % key)
    return dict(value)
