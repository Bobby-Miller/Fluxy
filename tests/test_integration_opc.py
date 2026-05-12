import os
import time

import pytest

import fluxy
from fluxy import FluxyError


@pytest.mark.integration
def test_opc_server_browse_read_and_write_against_disposable_simulator_device():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    device_name = os.getenv("FLUXY_OPC_TEST_DEVICE_NAME", "FluxyOpcSimulator")
    opc_server = os.getenv("FLUXY_OPC_SERVER", "Ignition OPC UA Server")

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        remove_if_present(fx, device_name)
        assert fx.device.add_device(
            "Simulator",
            device_name,
            device_props={"Enabled": 1},
            description="Fluxy disposable OPC integration test device",
        )
        eventually_device_present(fx, device_name)
        servers = eventually_opc_servers(fx, opc_server)
        state = eventually_opc_connected(fx, opc_server)
        browse_rows = eventually_opc_browse(fx, opc_server, device_name)
        browse_server_rows = eventually_opc_browse_server_device(fx, opc_server, device_name)
        browse_simple_rows = fx.opc.browse_simple(opc_server=opc_server, device=device_name)
        item_path = first_opc_item_path(browse_rows, read_only=True)
        writable_item_path = first_opc_item_path(browse_rows, read_only=False)
        value = fx.opc.read_value(opc_server, item_path)
        values = fx.opc.read_values(opc_server, [item_path])
        write_quality = fx.opc.write_value(opc_server, writable_item_path, 123)
        write_qualities = fx.opc.write_values(opc_server, [writable_item_path], [124])
        write_readback = fx.opc.read_value(opc_server, writable_item_path)
    except FluxyError as exc:
        pytest.fail("Fluxy OPC integration failed: %s\ndevice_name=%s" % (exc, device_name))
    finally:
        remove_if_present(fx, device_name)

    assert opc_server in servers
    assert state == "CONNECTED"
    assert any(device_name in str(row) for row in browse_server_rows), browse_server_rows
    assert first_opc_item_path(browse_simple_rows, read_only=True)
    assert item_path
    assert writable_item_path
    assert value.quality.startswith("Good"), value
    assert values and values[0].quality.startswith("Good"), values
    assert write_quality.startswith("Good"), write_quality
    assert all(quality.startswith("Good") for quality in write_qualities), write_qualities
    assert write_readback.quality.startswith("Good"), write_readback


def remove_if_present(fx, device_name):
    try:
        if any(device.name == device_name for device in fx.device.list_devices()):
            fx.device.remove_device(device_name)
    except FluxyError:
        pass


def eventually_device_present(fx, device_name):
    deadline = time.monotonic() + float(os.getenv("FLUXY_OPC_TIMEOUT_SECONDS", "25"))
    while time.monotonic() < deadline:
        if any(device.name == device_name for device in fx.device.list_devices()):
            return
        time.sleep(0.5)
    pytest.fail("OPC simulator device did not appear: %r" % device_name)


def eventually_opc_servers(fx, expected_server):
    deadline = time.monotonic() + float(os.getenv("FLUXY_OPC_TIMEOUT_SECONDS", "25"))
    last_servers = []
    while time.monotonic() < deadline:
        last_servers = fx.opc.get_servers(include_disabled=True)
        if expected_server in last_servers:
            return last_servers
        time.sleep(0.5)
    pytest.fail("OPC server did not appear: expected=%r last_servers=%r" % (expected_server, last_servers))


def eventually_opc_connected(fx, opc_server):
    deadline = time.monotonic() + float(os.getenv("FLUXY_OPC_TIMEOUT_SECONDS", "25"))
    last_state = None
    while time.monotonic() < deadline:
        last_state = fx.opc.get_server_state(opc_server)
        if last_state == "CONNECTED":
            return last_state
        time.sleep(0.5)
    pytest.fail("OPC server did not connect: server=%r last_state=%r" % (opc_server, last_state))


def eventually_opc_browse(fx, opc_server, device_name):
    deadline = time.monotonic() + float(os.getenv("FLUXY_OPC_TIMEOUT_SECONDS", "25"))
    last_rows = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_rows = fx.opc.browse(opc_server=opc_server, device=device_name)
            if first_opc_item_path(last_rows, read_only=True) and first_opc_item_path(
                last_rows, read_only=False
            ):
                return last_rows
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "OPC browse did not return item paths: server=%r device=%r last_rows=%r last_error=%s"
        % (opc_server, device_name, last_rows, last_error)
    )


def eventually_opc_browse_server_device(fx, opc_server, device_name):
    deadline = time.monotonic() + float(os.getenv("FLUXY_OPC_TIMEOUT_SECONDS", "25"))
    last_rows = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_rows = fx.opc.browse_server(opc_server, "Devices")
            if any(device_name in str(row) for row in last_rows):
                return last_rows
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "OPC browseServer did not return device: server=%r device=%r last_rows=%r last_error=%s"
        % (opc_server, device_name, last_rows, last_error)
    )


def first_opc_item_path(rows, read_only):
    for row in rows:
        item_path = row.get("opcItemPath")
        row_type = str(row.get("type"))
        text = str(row)
        if item_path and row_type == "DATAVARIABLE" and ("ReadOnly" in text) is read_only:
            return str(item_path)
    return None
