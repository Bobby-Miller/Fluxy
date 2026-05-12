import json

import pytest

from fluxy import Fluxy, FluxyError
from fluxy.named_query import (
    NAMED_QUERY_SQL_TYPES,
    add_named_query,
    delete_named_query,
    named_query_parameter,
)


def test_add_named_query_writes_resource_and_query_sql(tmp_path):
    path = add_named_query(tmp_path, "hello_world", "select message from hello", database="FluxyHello")

    resource = json.loads((path / "resource.json").read_text())

    assert (path / "query.sql").read_text() == "select message from hello\n"
    assert resource["scope"] == "DG"
    assert resource["version"] == 2
    assert resource["files"] == ["query.sql"]
    assert resource["attributes"]["type"] == "Query"
    assert resource["attributes"]["database"] == "FluxyHello"


def test_add_named_query_writes_parameters(tmp_path):
    path = add_named_query(
        tmp_path,
        "hello_world",
        "select :world",
        parameters=[{"type": "Parameter", "identifier": "world", "sqlType": 7}],
    )

    resource = json.loads((path / "resource.json").read_text())

    assert resource["attributes"]["parameters"] == [
        {"type": "Parameter", "identifier": "world", "sqlType": 7}
    ]


def test_named_query_sql_type_reference_matches_ignition_sample():
    assert NAMED_QUERY_SQL_TYPES == {
        "Int1": 0,
        "Int2": 1,
        "Int4": 2,
        "Int8": 3,
        "Float4": 4,
        "Float8": 5,
        "Boolean": 6,
        "String": 7,
        "DateTime": 8,
        "ByteArray": 20,
    }
    assert named_query_parameter("world", "String") == {
        "type": "Parameter",
        "identifier": "world",
        "sqlType": 7,
    }


def test_delete_named_query_removes_resource(tmp_path):
    path = add_named_query(tmp_path, "hello_world", "select 'hello'")

    deleted = delete_named_query(tmp_path, "hello_world")

    assert deleted == path
    assert not deleted.exists()


def test_named_query_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="inside ignition/named-query"):
        add_named_query(tmp_path, "../bad", "select 'bad'")


def test_fluxy_project_location_enables_named_query_add_delete(tmp_path):
    fx = Fluxy("https://ignition.example/system/webdev/Fluxy", project_location=tmp_path)

    path = fx.named_query.add_named_query("hello_world", "select 'hello'")
    deleted = fx.named_query.delete_named_query("hello_world")

    assert path == deleted
    assert not path.exists()


def test_fluxy_requires_project_location_for_named_query_add():
    fx = Fluxy("https://ignition.example/system/webdev/Fluxy")

    with pytest.raises(FluxyError, match="project_location is required"):
        fx.named_query.add_named_query("hello_world", "select 'hello'")
