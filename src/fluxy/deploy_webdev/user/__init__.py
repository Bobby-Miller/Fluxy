from __future__ import annotations

from ..common import COMMON
from ..resource import WebDevResource


USER_HELPERS = r"""


def _ui_response_to_wire(response):
    return {
        "warnings": [str(value) for value in response.getWarns()],
        "errors": [str(value) for value in response.getErrors()],
        "infos": [str(value) for value in response.getInfos()],
    }


def _user_to_wire(user):
    fields = {}
    for key in ["username", "firstname", "lastname", "email", "badge", "language", "notes", "schedule"]:
        try:
            value = user.get(key)
            if value is not None:
                fields[key] = str(value)
        except Exception:
            pass
    roles = []
    try:
        roles = [str(role) for role in user.getRoles()]
    except Exception:
        pass
    contact_info = []
    try:
        for contact in user.getContactInfo():
            contact_info.append(str(contact))
    except Exception:
        pass
    username = fields.get("username")
    if username is None:
        try:
            username = str(user.getUserName())
        except Exception:
            username = ""
    return {"username": username, "fields": fields, "roles": roles, "contactInfo": contact_info}


def _schedule_to_wire(schedule):
    return {
        "name": str(schedule.getName()),
        "description": str(schedule.getDescription()),
        "type": str(schedule.getType()),
        "observeHolidays": bool(schedule.isObserveHolidays()),
    }


def _holiday_to_wire(holiday):
    return {
        "name": str(holiday.getName()),
        "date": holiday.getDate().getTime(),
        "repeatAnnually": bool(holiday.isRepeatAnnually()),
    }


def _apply_user_payload(user, payload, include_password):
    fields = payload.get("fields") or {}
    if not isinstance(fields, dict):
        raise ValueError("fields must be an object")
    for key, value in fields.items():
        user.set(str(key), value)
    if include_password:
        password = payload.get("password")
        if not isinstance(password, basestring):
            raise ValueError("password string is required")
        user.set("password", password)
    roles = payload.get("roles") or []
    if not isinstance(roles, list):
        raise ValueError("roles must be a list")
    if roles:
        user.addRoles([str(role) for role in roles])
    contact_info = payload.get("contactInfo") or payload.get("contact_info") or {}
    if not isinstance(contact_info, dict):
        raise ValueError("contactInfo must be an object")
    if contact_info:
        user.addContactInfo(dict((str(key), str(value)) for key, value in contact_info.items()))
    return user
"""


GET_USER_SOURCES_POST = (
    COMMON
    + r"""


def doPost(request, session):
    operation = "User.getUserSources"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        sources = []
        for source in system.user.getUserSources():
            sources.append({"name": str(source.name), "description": str(source.description), "type": str(source.type)})
        _log_success(operation)
        return {"json": {"ok": True, "sources": sources}}
    except Exception, exc:
        _log_error(operation, "getUserSources failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


GET_ROLES_POST = (
    COMMON
    + r"""


def doPost(request, session):
    operation = "User.getRoles"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        user_source = payload.get("userSource") or payload.get("user_source")
        if not isinstance(user_source, basestring):
            return _bad_request("Request must include userSource string", _request_debug(request))
        roles = [str(role) for role in system.user.getRoles(user_source)]
        _log_success(operation)
        return {"json": {"ok": True, "roles": roles}}
    except Exception, exc:
        _log_error(operation, "getRoles failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


ADD_ROLE_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.addRole"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        response = system.user.addRole(payload.get("userSource") or payload.get("user_source"), payload.get("role"))
        result = _ui_response_to_wire(response)
        _log_success(operation)
        result["ok"] = len(result["errors"]) == 0
        return {"json": result}
    except Exception, exc:
        _log_error(operation, "addRole failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


EDIT_ROLE_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.editRole"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        response = system.user.editRole(
            payload.get("userSource") or payload.get("user_source"),
            payload.get("oldName") or payload.get("old_name"),
            payload.get("newName") or payload.get("new_name"),
        )
        result = _ui_response_to_wire(response)
        _log_success(operation)
        result["ok"] = len(result["errors"]) == 0
        return {"json": result}
    except Exception, exc:
        _log_error(operation, "editRole failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


REMOVE_ROLE_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.removeRole"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        response = system.user.removeRole(payload.get("userSource") or payload.get("user_source"), payload.get("role"))
        result = _ui_response_to_wire(response)
        _log_success(operation)
        result["ok"] = len(result["errors"]) == 0
        return {"json": result}
    except Exception, exc:
        _log_error(operation, "removeRole failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


ADD_USER_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.addUser"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        user_source = payload.get("userSource") or payload.get("user_source")
        username = payload.get("username")
        if not isinstance(user_source, basestring) or not isinstance(username, basestring):
            return _bad_request("Request must include userSource and username strings", _request_debug(request))
        user = system.user.getNewUser(user_source, username)
        _apply_user_payload(user, payload, True)
        response = system.user.addUser(user_source, user)
        result = _ui_response_to_wire(response)
        _log_success(operation)
        result["ok"] = len(result["errors"]) == 0
        return {"json": result}
    except Exception, exc:
        _log_error(operation, "addUser failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


GET_USER_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.getUser"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        user = system.user.getUser(payload.get("userSource") or payload.get("user_source"), payload.get("username"))
        _log_success(operation)
        return {"json": {"ok": True, "user": _user_to_wire(user)}}
    except Exception, exc:
        _log_error(operation, "getUser failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


GET_USERS_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.getUsers"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        users = [_user_to_wire(user) for user in system.user.getUsers(payload.get("userSource") or payload.get("user_source"))]
        _log_success(operation)
        return {"json": {"ok": True, "users": users}}
    except Exception, exc:
        _log_error(operation, "getUsers failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


EDIT_USER_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.editUser"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        user_source = payload.get("userSource") or payload.get("user_source")
        username = payload.get("username")
        user = system.user.getUser(user_source, username)
        _apply_user_payload(user, payload, payload.get("password") is not None)
        response = system.user.editUser(user_source, user)
        result = _ui_response_to_wire(response)
        _log_success(operation)
        result["ok"] = len(result["errors"]) == 0
        return {"json": result}
    except Exception, exc:
        _log_error(operation, "editUser failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


REMOVE_USER_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.removeUser"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        response = system.user.removeUser(payload.get("userSource") or payload.get("user_source"), payload.get("username"))
        result = _ui_response_to_wire(response)
        _log_success(operation)
        result["ok"] = len(result["errors"]) == 0
        return {"json": result}
    except Exception, exc:
        _log_error(operation, "removeUser failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


ADD_SCHEDULE_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.addSchedule"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        name = payload.get("name")
        source_schedule = payload.get("sourceSchedule") or payload.get("source_schedule") or "Always"
        description = payload.get("description") or ""
        if not isinstance(name, basestring):
            return _bad_request("Request must include name string", _request_debug(request))
        schedule = system.user.getSchedule(source_schedule)
        schedule.setName(name)
        schedule.setDescription(description)
        response = system.user.addSchedule(schedule)
        result = _ui_response_to_wire(response)
        _log_success(operation)
        result["ok"] = len(result["errors"]) == 0
        return {"json": result}
    except Exception, exc:
        _log_error(operation, "addSchedule failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


GET_SCHEDULE_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.getSchedule"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        schedule = system.user.getSchedule(payload.get("name"))
        _log_success(operation)
        return {"json": {"ok": True, "schedule": _schedule_to_wire(schedule)}}
    except Exception, exc:
        _log_error(operation, "getSchedule failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


GET_SCHEDULES_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.getSchedules"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        schedules = [_schedule_to_wire(schedule) for schedule in system.user.getSchedules()]
        _log_success(operation)
        return {"json": {"ok": True, "schedules": schedules}}
    except Exception, exc:
        _log_error(operation, "getSchedules failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


REMOVE_SCHEDULE_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.removeSchedule"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        response = system.user.removeSchedule(payload.get("name"))
        result = _ui_response_to_wire(response)
        _log_success(operation)
        result["ok"] = len(result["errors"]) == 0
        return {"json": result}
    except Exception, exc:
        _log_error(operation, "removeSchedule failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


ADD_HOLIDAY_POST = (
    COMMON
    + USER_HELPERS
    + r"""

from com.inductiveautomation.ignition.common.user.schedule import HolidayModel


def doPost(request, session):
    operation = "User.addHoliday"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        name = payload.get("name")
        date = payload.get("date")
        repeat_annually = payload.get("repeatAnnually")
        if repeat_annually is None:
            repeat_annually = payload.get("repeat_annually") or False
        if not isinstance(name, basestring):
            return _bad_request("Request must include name string", _request_debug(request))
        if date is None:
            return _bad_request("Request must include date millis", _request_debug(request))
        holiday = HolidayModel(name, system.date.fromMillis(long(date)), bool(repeat_annually))
        response = system.user.addHoliday(holiday)
        result = _ui_response_to_wire(response)
        _log_success(operation)
        result["ok"] = len(result["errors"]) == 0
        return {"json": result}
    except Exception, exc:
        _log_error(operation, "addHoliday failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


GET_HOLIDAY_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.getHoliday"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        holiday = system.user.getHoliday(payload.get("name"))
        _log_success(operation)
        return {"json": {"ok": True, "holiday": _holiday_to_wire(holiday)}}
    except Exception, exc:
        _log_error(operation, "getHoliday failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


GET_HOLIDAYS_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.getHolidays"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        holidays = [_holiday_to_wire(holiday) for holiday in system.user.getHolidays()]
        _log_success(operation)
        return {"json": {"ok": True, "holidays": holidays}}
    except Exception, exc:
        _log_error(operation, "getHolidays failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


REMOVE_HOLIDAY_POST = (
    COMMON
    + USER_HELPERS
    + r"""


def doPost(request, session):
    operation = "User.removeHoliday"
    if not _auth_ok(request):
        return _unauthorized()
    try:
        _log_start(operation)
        payload = _json_body(request)
        response = system.user.removeHoliday(payload.get("name"))
        result = _ui_response_to_wire(response)
        _log_success(operation)
        result["ok"] = len(result["errors"]) == 0
        return {"json": result}
    except Exception, exc:
        _log_error(operation, "removeHoliday failed", exc)
        return {"json": {"ok": False, "error": str(exc)}, "status": 500}
"""
)


RESOURCES = [
    WebDevResource("user/getUserSources", "getUserSources", GET_USER_SOURCES_POST),
    WebDevResource("user/getRoles", "getRoles", GET_ROLES_POST),
    WebDevResource("user/addRole", "addRole", ADD_ROLE_POST),
    WebDevResource("user/editRole", "editRole", EDIT_ROLE_POST),
    WebDevResource("user/removeRole", "removeRole", REMOVE_ROLE_POST),
    WebDevResource("user/addUser", "addUser", ADD_USER_POST),
    WebDevResource("user/getUser", "getUser", GET_USER_POST),
    WebDevResource("user/getUsers", "getUsers", GET_USERS_POST),
    WebDevResource("user/editUser", "editUser", EDIT_USER_POST),
    WebDevResource("user/removeUser", "removeUser", REMOVE_USER_POST),
    WebDevResource("user/addSchedule", "addSchedule", ADD_SCHEDULE_POST),
    WebDevResource("user/getSchedule", "getSchedule", GET_SCHEDULE_POST),
    WebDevResource("user/getSchedules", "getSchedules", GET_SCHEDULES_POST),
    WebDevResource("user/removeSchedule", "removeSchedule", REMOVE_SCHEDULE_POST),
    WebDevResource("user/addHoliday", "addHoliday", ADD_HOLIDAY_POST),
    WebDevResource("user/getHoliday", "getHoliday", GET_HOLIDAY_POST),
    WebDevResource("user/getHolidays", "getHolidays", GET_HOLIDAYS_POST),
    WebDevResource("user/removeHoliday", "removeHoliday", REMOVE_HOLIDAY_POST),
]
