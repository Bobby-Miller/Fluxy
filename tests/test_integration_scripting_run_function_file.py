import os
import time

import pytest

import fluxy
from fluxy import FluxyError


@pytest.mark.integration
def test_run_hello_world_function_file():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    target_directory = os.getenv("FLUXY_SCRIPTING_TARGET_DIRECTORY", "integration_run")

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.scripting.deploy_function_file("hello_world.py", target_directory=target_directory)
        fx.project.request_scan()
        result = eventually_run_function_file(fx, "hello_world.py", target_directory=target_directory)
    except FluxyError as exc:
        pytest.fail("Fluxy scripting run_function_file failed: %s" % exc)
    finally:
        try:
            fx.scripting.delete_function_file("hello_world.py", target_directory=target_directory)
            fx.project.request_scan()
        except FluxyError:
            pass

    assert result.ok is True
    assert result.result == "Hello World!"


@pytest.mark.integration
def test_deploy_run_delete_then_run_fails_for_hello_world_function_file():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    target_directory = os.getenv("FLUXY_SCRIPTING_CYCLE_TARGET_DIRECTORY", "cycle")

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.scripting.deploy_function_file("hello_world.py", target_directory=target_directory)
        fx.project.request_scan()
        result = eventually_run_function_file(fx, "hello_world.py", target_directory=target_directory)
        fx.scripting.delete_function_file("hello_world.py", target_directory=target_directory)
        fx.project.request_scan()
    except FluxyError as exc:
        pytest.fail("Fluxy scripting deploy/run/delete cycle setup failed: %s" % exc)

    assert result.ok is True
    assert result.result == "Hello World!"

    with pytest.raises(FluxyError):
        eventually_run_function_file(fx, "hello_world.py", target_directory=target_directory, expect_success=False)


def eventually_run_function_file(fx, file_name, target_directory=None, expect_success=True):
    deadline = time.monotonic() + float(os.getenv("FLUXY_SCRIPTING_LOAD_TIMEOUT_SECONDS", "8"))
    last_error = None
    while time.monotonic() < deadline:
        try:
            result = fx.scripting.run_function_file(file_name, target_directory=target_directory)
            if expect_success:
                return result
            last_error = FluxyError("function still runs")
        except FluxyError as exc:
            if not expect_success:
                raise
            last_error = exc
        time.sleep(0.25)
    raise FluxyError("Function file %s did not reach expected state: %s" % (file_name, last_error))
