import os

import pytest

import fluxy
from fluxy import FluxyError


@pytest.mark.integration
def test_project_request_scan():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        result = fx.project.request_scan()
        project_name = fx.project.get_project_name()
        project_names = fx.project.get_project_names()
    except FluxyError as exc:
        pytest.fail("Fluxy project integration failed: %s" % exc)

    assert result.ok is True
    assert project_name
    assert project_name in project_names
