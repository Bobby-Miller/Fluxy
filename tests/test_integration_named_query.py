import os
import time
from datetime import datetime

import pytest

import fluxy
from fluxy import FluxyError
from fluxy.named_query import named_query_parameter


pytestmark = pytest.mark.integration


def test_add_run_delete_named_query_cycle():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    database = os.getenv("FLUXY_DB_NAME", "FluxyHello")
    query_name = os.getenv("FLUXY_NAMED_QUERY_NAME", "hello_world")

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        fx.named_query.add_named_query(
            query_name,
            "select message from hello where id = 1",
            database=database,
        )
        fx.project.request_scan()
        result = eventually_run_named_query(fx, query_name)
        fx.named_query.delete_named_query(query_name)
        fx.project.request_scan()
    except FluxyError as exc:
        pytest.fail("Fluxy named query cycle setup failed for %s: %s" % (query_name, exc))
    finally:
        try:
            fx.named_query.delete_named_query(query_name)
            fx.project.request_scan()
        except FluxyError:
            pass

    assert result == [{"message": "Hello from SQLite"}]

    assert_named_query_eventually_unloads(fx, query_name)


def test_run_named_query_returns_multiple_rows():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    database = os.getenv("FLUXY_DB_NAME", "FluxyHello")
    query_name = os.getenv("FLUXY_MULTI_ROW_NAMED_QUERY_NAME", "fluxy_multi_row_round_trip")

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        fx.named_query.add_named_query(
            query_name,
            """
select 1 as id, message from hello where id = 1
union all
select 2 as id, message from hello where id = 1
order by id
""",
            database=database,
        )
        fx.project.request_scan()
        result = eventually_run_named_query(fx, query_name)
        fx.named_query.delete_named_query(query_name)
        fx.project.request_scan()
    except FluxyError as exc:
        pytest.fail("Fluxy multi-row named query cycle failed for %s: %s" % (query_name, exc))
    finally:
        try:
            fx.named_query.delete_named_query(query_name)
            fx.project.request_scan()
        except FluxyError:
            pass

    assert_named_query_eventually_unloads(fx, query_name)
    assert result == [
        {"id": 1, "message": "Hello from SQLite"},
        {"id": 2, "message": "Hello from SQLite"},
    ]
    assert result.columns == ["id", "message"]
    assert result.source == "ignition.dataset"
    assert result.message == "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings"


def test_run_named_query_with_typed_parameters():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    database = os.getenv("FLUXY_DB_NAME", "FluxyHello")
    query_name = os.getenv("FLUXY_TYPED_NAMED_QUERY_NAME", "fluxy_parameter_round_trip")
    datetime_value = "2026-05-11 20:59:37"

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)
    parameters = {
        "world": "Hello typed world",
        "newValue3": 123456,
        "newValue6": 123.456,
        "newValue7": True,
        "newValue8": datetime_value,
    }

    try:
        fx.named_query.add_named_query(
            query_name,
            """
select
  :world as world,
  :newValue3 as newValue3,
  :newValue6 as newValue6,
  :newValue7 as newValue7,
  :newValue8 as newValue8
""",
            database=database,
            parameters=[
                named_query_parameter("world", "String"),
                named_query_parameter("newValue3", "Int4"),
                named_query_parameter("newValue6", "Float8"),
                named_query_parameter("newValue7", "Boolean"),
                named_query_parameter("newValue8", "DateTime"),
            ],
        )
        fx.project.request_scan()
        result = eventually_run_named_query(fx, query_name, parameters=parameters)
        fx.named_query.delete_named_query(query_name)
        fx.project.request_scan()
    except FluxyError as exc:
        pytest.fail("Fluxy typed named query cycle failed for %s: %s" % (query_name, exc))
    finally:
        try:
            fx.named_query.delete_named_query(query_name)
            fx.project.request_scan()
        except FluxyError:
            pass

    assert_named_query_eventually_unloads(fx, query_name)

    assert len(result) == 1
    row = result[0]
    assert row["world"] == parameters["world"]
    assert row["newValue3"] == parameters["newValue3"]
    assert row["newValue6"] == pytest.approx(parameters["newValue6"])
    assert row["newValue7"] in [True, 1]
    assert row["newValue8"] == int(datetime.fromisoformat(datetime_value).astimezone().timestamp() * 1000)


def assert_named_query_eventually_unloads(fx, query_name):
    deadline = time.monotonic() + float(os.getenv("FLUXY_NAMED_QUERY_DELETE_TIMEOUT_SECONDS", "8"))
    last_result = None
    while time.monotonic() < deadline:
        try:
            last_result = fx.db.run_named_query(query_name)
        except FluxyError:
            return
        time.sleep(0.25)
    pytest.fail("Named query %s still ran after delete and scan: %r" % (query_name, last_result))


def eventually_run_named_query(fx, query_name, parameters=None):
    deadline = time.monotonic() + float(os.getenv("FLUXY_NAMED_QUERY_LOAD_TIMEOUT_SECONDS", "8"))
    last_error = None
    while time.monotonic() < deadline:
        try:
            return fx.db.run_named_query(query_name, parameters=parameters)
        except FluxyError as exc:
            last_error = exc
            time.sleep(0.25)
    raise FluxyError("Named query %s did not load after scan: %s" % (query_name, last_error))
