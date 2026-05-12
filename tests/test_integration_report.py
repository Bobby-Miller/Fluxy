import os

import pytest

import fluxy
from fluxy import FluxyError


@pytest.mark.integration
def test_report_names_and_execute_test_report_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    report_name = os.getenv("FLUXY_REPORT_NAME", "test_Report")

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        project_name = fx.project.get_project_name()
        names = fx.report.get_report_names_as_list(project_name)
        rows = fx.report.get_report_names_as_dataset(project_name)
        result = fx.report.execute_report(report_name, project_name, file_type="pdf")
    except FluxyError as exc:
        pytest.fail("Fluxy report integration failed: %s" % exc)

    assert report_name in names
    assert any(report_name in [str(value) for value in row.values()] for row in rows)
    assert result.file_type == "pdf"
    assert result.content.startswith(b"%PDF")
