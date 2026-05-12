import os
import time
from uuid import uuid4

import pytest

import fluxy
from fluxy import FluxyError


@pytest.mark.integration
def test_userdb_role_and_user_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    user_source = os.getenv("FLUXY_USER_SOURCE", "userDB")
    suffix = uuid4().hex
    role = "fluxy_role_" + suffix
    edited_role = "fluxy_role_edited_" + suffix
    username = "fluxy_user_" + suffix

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        sources = fx.user.get_user_sources()
        source_names = [str(source.get("name")) for source in sources]
        matched_sources = [name for name in source_names if name.lower() == user_source.lower()]
        assert matched_sources, source_names
        user_source = matched_sources[0]

        add_role = fx.user.add_role(user_source, role)
        assert add_role.ok, add_role
        assert role in fx.user.get_roles(user_source)

        edit_role = fx.user.edit_role(user_source, role, edited_role)
        assert edit_role.ok, edit_role
        assert edited_role in fx.user.get_roles(user_source)
        role = edited_role

        add_user = fx.user.add_user(
            user_source,
            username,
            "FluxyTestPassword123!",
            fields={"firstname": "Fluxy", "lastname": "Integration"},
            roles=[role],
            contact_info={"email": username + "@example.invalid"},
        )
        assert add_user.ok, add_user
        created = fx.user.get_user(user_source, username)

        edit_user = fx.user.edit_user(
            user_source,
            username,
            fields={"firstname": "FluxyEdited", "lastname": "Integration"},
            roles=[role],
        )
        assert edit_user.ok, edit_user
        edited = fx.user.get_user(user_source, username)
        users = fx.user.get_users(user_source)
    except FluxyError as exc:
        pytest.fail("Fluxy user integration failed during setup: %s" % exc)
    finally:
        try:
            fx.user.remove_user(user_source, username)
        except FluxyError:
            pass
        try:
            fx.user.remove_role(user_source, role)
        except FluxyError:
            pass
        try:
            fx.user.remove_role(user_source, edited_role)
        except FluxyError:
            pass

    assert created["username"] == username
    assert role in created["roles"]
    assert edited["fields"].get("firstname") == "FluxyEdited"
    assert any(user.get("username") == username for user in users)

    eventually_assert_user_removed(fx, user_source, username)
    eventually_assert_role_removed(fx, user_source, role)


@pytest.mark.integration
def test_schedule_and_holiday_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    suffix = uuid4().hex
    schedule_name = "fluxy_schedule_" + suffix
    holiday_name = "fluxy_holiday_" + suffix
    holiday_date = 2_114_904_400_000  # 2037-01-02T05:00:00Z, local midnight EST.

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        add_schedule = fx.user.add_schedule(
            schedule_name, source_schedule="Always", description="Fluxy disposable schedule"
        )
        assert add_schedule.ok, add_schedule
        schedule = fx.user.get_schedule(schedule_name)
        schedules = fx.user.get_schedules()

        add_holiday = fx.user.add_holiday(holiday_name, holiday_date, repeat_annually=False)
        assert add_holiday.ok, add_holiday
        holiday = fx.user.get_holiday(holiday_name)
        holidays = fx.user.get_holidays()
    except FluxyError as exc:
        pytest.fail("Fluxy schedule/holiday integration failed during setup: %s" % exc)
    finally:
        try:
            fx.user.remove_schedule(schedule_name)
        except FluxyError:
            pass
        try:
            fx.user.remove_holiday(holiday_name)
        except FluxyError:
            pass

    assert schedule["name"] == schedule_name
    assert schedule["description"] == "Fluxy disposable schedule"
    assert any(row.get("name") == schedule_name for row in schedules)
    assert holiday["name"] == holiday_name
    assert holiday["repeatAnnually"] is False
    assert any(row.get("name") == holiday_name for row in holidays)

    eventually_assert_schedule_removed(fx, schedule_name)
    eventually_assert_holiday_removed(fx, holiday_name)


def eventually_assert_user_removed(fx, user_source, username):
    deadline = time.monotonic() + float(os.getenv("FLUXY_USER_TIMEOUT_SECONDS", "10"))
    while time.monotonic() < deadline:
        if all(user.get("username") != username for user in fx.user.get_users(user_source)):
            return
        time.sleep(0.5)
    pytest.fail("User was not removed from %s: %s" % (user_source, username))


def eventually_assert_role_removed(fx, user_source, role):
    deadline = time.monotonic() + float(os.getenv("FLUXY_USER_TIMEOUT_SECONDS", "10"))
    while time.monotonic() < deadline:
        if role not in fx.user.get_roles(user_source):
            return
        try:
            fx.user.remove_role(user_source, role)
        except FluxyError:
            pass
        time.sleep(0.5)
    pytest.fail("Role was not removed from %s: %s" % (user_source, role))


def eventually_assert_schedule_removed(fx, name):
    deadline = time.monotonic() + float(os.getenv("FLUXY_USER_TIMEOUT_SECONDS", "10"))
    while time.monotonic() < deadline:
        if all(schedule.get("name") != name for schedule in fx.user.get_schedules()):
            return
        try:
            fx.user.remove_schedule(name)
        except FluxyError:
            pass
        time.sleep(0.5)
    pytest.fail("Schedule was not removed: %s" % name)


def eventually_assert_holiday_removed(fx, name):
    deadline = time.monotonic() + float(os.getenv("FLUXY_USER_TIMEOUT_SECONDS", "10"))
    while time.monotonic() < deadline:
        if all(holiday.get("name") != name for holiday in fx.user.get_holidays()):
            return
        try:
            fx.user.remove_holiday(name)
        except FluxyError:
            pass
        time.sleep(0.5)
    pytest.fail("Holiday was not removed: %s" % name)
