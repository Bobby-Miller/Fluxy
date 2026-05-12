import os
import time

import pytest

import fluxy
from fluxy import FluxyError


@pytest.mark.integration
def test_add_list_update_and_remove_simulator_device_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    device_name = os.getenv("FLUXY_DEVICE_TEST_NAME", "FluxyTemporarySimulator")

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        remove_if_present(fx, device_name)
        eventually_device_absent(fx, device_name)

        assert fx.device.add_device(
            "Simulator",
            device_name,
            device_props={"Enabled": 0},
            description="Fluxy disposable integration test device",
        )
        added = eventually_device_present(fx, device_name)

        assert added.name == device_name
        assert added.driver is None or "sim" in added.driver.lower()
        assert fx.device.set_device_enabled(device_name, False)
        eventually_device_enabled(fx, device_name, False)

        assert fx.device.remove_device(device_name)
        eventually_device_absent(fx, device_name)
    except FluxyError as exc:
        pytest.fail("Fluxy device integration failed: %s\ndevice_name=%s" % (exc, device_name))
    finally:
        remove_if_present(fx, device_name)


def remove_if_present(fx, device_name):
    if find_device(fx, device_name) is not None:
        try:
            fx.device.remove_device(device_name)
        except FluxyError:
            pass


def eventually_device_present(fx, device_name):
    deadline = time.monotonic() + float(os.getenv("FLUXY_DEVICE_TIMEOUT_SECONDS", "20"))
    last_devices = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_devices = fx.device.list_devices()
            device = first_device(last_devices, device_name)
            if device is not None:
                return device
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Device did not appear: device_name=%r last_devices=%r last_error=%s"
        % (device_name, last_devices, last_error)
    )


def eventually_device_absent(fx, device_name):
    deadline = time.monotonic() + float(os.getenv("FLUXY_DEVICE_TIMEOUT_SECONDS", "20"))
    last_devices = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_devices = fx.device.list_devices()
            if first_device(last_devices, device_name) is None:
                return
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Device did not disappear: device_name=%r last_devices=%r last_error=%s"
        % (device_name, last_devices, last_error)
    )


def eventually_device_enabled(fx, device_name, expected_enabled):
    deadline = time.monotonic() + float(os.getenv("FLUXY_DEVICE_TIMEOUT_SECONDS", "20"))
    last_device = None
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_device = first_device(fx.device.list_devices(), device_name)
            if last_device is not None and last_device.enabled is expected_enabled:
                return last_device
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Device enabled state did not update: device_name=%r expected=%r last_device=%r last_error=%s"
        % (device_name, expected_enabled, last_device, last_error)
    )


def find_device(fx, device_name):
    try:
        return first_device(fx.device.list_devices(), device_name)
    except FluxyError:
        return None


def first_device(devices, device_name):
    for device in devices:
        if device.name == device_name:
            return device
    return None
