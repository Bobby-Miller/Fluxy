import os
import time
from urllib.parse import urlparse
from uuid import uuid4

import pytest

import fluxy
from fluxy import FluxyError


@pytest.mark.integration
def test_util_diagnostics_against_live_gateway():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    gateway_address = os.getenv("FLUXY_GATEWAY_STATUS_ADDRESS") or address_from_base_url(base_url)

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        version = eventually_get_version(fx)
        modules = fx.util.get_modules()
        status = fx.util.get_gateway_status(
            gateway_address,
            connect_timeout_millis=5_000,
            socket_timeout_millis=5_000,
        )
        project_name = fx.util.get_project_name()
    except FluxyError as exc:
        pytest.fail("Fluxy util integration failed: %s" % exc)

    assert version.version
    assert version.major is not None
    assert version.minor is not None
    assert modules
    assert any("Name" in module or "name" in module for module in modules)
    assert status == "RUNNING"
    assert project_name


@pytest.mark.integration
def test_util_audit_and_query_audit_log_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    audit_profile = os.getenv("FLUXY_AUDIT_PROFILE", "Audit")
    unique = "fluxy-audit-%s" % uuid4().hex
    now_millis = int(time.time() * 1000)

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        eventually_get_version(fx)
        assert fx.util.audit(
            "FluxyIntegrationAudit",
            action_target=unique,
            action_value="created",
            audit_profile=audit_profile,
            actor="fluxy",
            actor_host="fluxy-test",
            originating_system="fluxy:integration:%s" % unique,
            event_timestamp=now_millis,
            originating_context=1,
            status_code=0,
        )
        rows = eventually_query_audit_row(fx, audit_profile, unique, now_millis)
    except FluxyError as exc:
        pytest.fail("Fluxy util audit integration failed: %s" % exc)

    assert rows
    assert any(unique in str(row) for row in rows)


def address_from_base_url(base_url):
    parsed = urlparse(base_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return "%s:%s" % (parsed.hostname or "localhost", port)


def eventually_get_version(fx):
    deadline = time.monotonic() + float(os.getenv("FLUXY_UTIL_TIMEOUT_SECONDS", "12"))
    last_error = None
    while time.monotonic() < deadline:
        try:
            return fx.util.get_version()
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail("Util getVersion did not become available: last_error=%s" % last_error)


def eventually_query_audit_row(fx, audit_profile, unique, event_millis):
    deadline = time.monotonic() + float(os.getenv("FLUXY_AUDIT_TIMEOUT_SECONDS", "12"))
    last_rows = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_rows = fx.util.query_audit_log(
                audit_profile,
                start_date=event_millis - 60_000,
                end_date=event_millis + 60_000,
                action_filter="FluxyIntegrationAudit",
                target_filter=unique,
            )
            if any(unique in str(row) for row in last_rows):
                return last_rows
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Audit row did not appear: profile=%r unique=%r last_rows=%r last_error=%s"
        % (audit_profile, unique, last_rows, last_error)
    )
