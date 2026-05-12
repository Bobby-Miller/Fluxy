import os
import time
from uuid import uuid4

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


@pytest.mark.integration
def test_alarm_query_shelve_unshelve_and_acknowledge_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    provider_name = os.getenv("FLUXY_TAG_PROVIDER", "default")
    provider_path = "[%s]" % provider_name
    folder_name = "FluxyAlarmIntegration_%s" % uuid4().hex
    tag_name = "AlarmFloat"
    alarm_name = "HighAlarm"
    tag_path = join_tag_path(provider_path, folder_name, tag_name)
    alarm_source = "prov:%s:/tag:%s/%s:/alm:%s" % (provider_name, folder_name, tag_name, alarm_name)

    fx = fluxy.Fluxy(
        base_url=base_url,
        token=token,
        project_location=project_location,
        tag_provider=provider_name,
    )

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        fx.tag.configure(
            [
                {
                    "name": folder_name,
                    "tagType": "Folder",
                    "tags": [
                        {
                            "name": tag_name,
                            "tagType": "AtomicTag",
                            "valueSource": "memory",
                            "dataType": "Float4",
                            "value": 0.0,
                            "alarms": [
                                {
                                    "name": alarm_name,
                                    "mode": "AboveValue",
                                    "setpointA": 10.0,
                                    "priority": "High",
                                }
                            ],
                        }
                    ],
                }
            ],
            base_path=provider_path,
            collision_policy="o",
        )
        fx.tag.write_blocking(tag_path, 20.0)
        active_rows = eventually_alarm_rows(fx, alarm_source, min_rows=1)
        event_ids = row_values_for_key(active_rows, "EventId")

        assert fx.alarm.shelve([alarm_source], timeout_seconds=60)
        eventually_shelved_path(fx, alarm_source)

        assert fx.alarm.unshelve([alarm_source])
        eventually_unshelved_path(fx, alarm_source)

        if event_ids:
            failed = fx.alarm.acknowledge(event_ids, notes="Fluxy alarm integration", username="fluxy")
            assert failed == []
    except FluxyError as exc:
        pytest.fail("Fluxy alarm integration failed: %s\nalarm_source=%s" % (exc, alarm_source))
    finally:
        try:
            fx.alarm.unshelve([alarm_source])
        except FluxyError:
            pass
        try:
            fx.tag.delete_tags([join_tag_path(provider_path, folder_name)])
        except FluxyError:
            pass


def eventually_alarm_rows(fx, alarm_source, min_rows):
    deadline = time.monotonic() + float(os.getenv("FLUXY_ALARM_TIMEOUT_SECONDS", "20"))
    last_rows = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_rows = fx.alarm.query_status(source=[alarm_source], include_shelved=True)
            if len(last_rows) >= min_rows:
                return last_rows
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Alarm rows did not appear: source=%r last_rows=%r last_error=%s"
        % (alarm_source, last_rows, last_error)
    )


def eventually_shelved_path(fx, alarm_source):
    deadline = time.monotonic() + float(os.getenv("FLUXY_ALARM_TIMEOUT_SECONDS", "20"))
    last_paths = []
    while time.monotonic() < deadline:
        last_paths = fx.alarm.get_shelved_paths()
        if any(alarm_source in str(path) for path in last_paths):
            return last_paths
        time.sleep(0.5)
    pytest.fail("Alarm was not shelved: source=%r last_paths=%r" % (alarm_source, last_paths))


def eventually_unshelved_path(fx, alarm_source):
    deadline = time.monotonic() + float(os.getenv("FLUXY_ALARM_TIMEOUT_SECONDS", "20"))
    last_paths = []
    while time.monotonic() < deadline:
        last_paths = fx.alarm.get_shelved_paths()
        if not any(alarm_source in str(path) for path in last_paths):
            return
        time.sleep(0.5)
    pytest.fail("Alarm was not unshelved: source=%r last_paths=%r" % (alarm_source, last_paths))


def row_values_for_key(rows, key):
    values = []
    lowered = key.lower()
    for row in rows:
        for row_key, value in row.items():
            if str(row_key).lower() == lowered and value is not None:
                values.append(str(value))
    return values
