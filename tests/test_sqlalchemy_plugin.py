import pytest
import httpx

from fluxy import Fluxy, FluxyError
from fluxy.named_query import add_named_query
from fluxy.plugins.sqlalchemy import SQLAlchemyNamedQueryRunner

sqlalchemy = pytest.importorskip("sqlalchemy")


def test_sqlalchemy_named_query_runner_executes_simple_project_named_query(tmp_path):
    add_named_query(tmp_path, "hello_world", "select 'Hello from SQLAlchemy' as message")
    fx = Fluxy(
        "https://ignition.example/system/webdev/Fluxy",
        project_location=tmp_path,
        named_query_runner=SQLAlchemyNamedQueryRunner(sqlalchemy.create_engine("sqlite+pysqlite:///:memory:")),
    )

    result = fx.db.run_named_query("hello_world")

    assert result == [{"message": "Hello from SQLAlchemy"}]


def test_sqlalchemy_named_query_runner_returns_multiple_row_mappings(tmp_path):
    add_named_query(
        tmp_path,
        "multi_row",
        """
select 1 as id, 'first' as message
union all
select 2 as id, 'second' as message
order by id
""",
    )
    fx = Fluxy(
        "https://ignition.example/system/webdev/Fluxy",
        project_location=tmp_path,
        named_query_runner=SQLAlchemyNamedQueryRunner(sqlalchemy.create_engine("sqlite+pysqlite:///:memory:")),
    )

    result = fx.db.run_named_query("multi_row")

    assert result == [
        {"id": 1, "message": "first"},
        {"id": 2, "message": "second"},
    ]
    assert result.columns == ["id", "message"]
    assert result.source == "sqlalchemy"
    assert result.message == "SQLAlchemy Result converted to Fluxy row mappings"


def test_sqlalchemy_named_query_runner_executes_typed_project_named_query(tmp_path):
    add_named_query(
        tmp_path,
        "typed_parameters",
        """
select
  :world as world,
  :newValue3 as newValue3,
  :newValue6 as newValue6,
  :newValue7 as newValue7,
  :newValue8 as newValue8
""",
    )
    engine = sqlalchemy.create_engine("sqlite+pysqlite:///:memory:")
    runner = SQLAlchemyNamedQueryRunner(engine)
    fx = Fluxy(
        "https://ignition.example/system/webdev/Fluxy",
        project_location=tmp_path,
        named_query_runner=runner,
    )

    result = fx.db.run_named_query(
        "typed_parameters",
        parameters={
            "world": "Hello SQLAlchemy",
            "newValue3": 123456,
            "newValue6": 123.456,
            "newValue7": True,
            "newValue8": "2026-05-11 20:59:37",
        },
    )

    assert result == [
        {
            "world": "Hello SQLAlchemy",
            "newValue3": 123456,
            "newValue6": pytest.approx(123.456),
            "newValue7": 1,
            "newValue8": "2026-05-11 20:59:37",
        }
    ]


def test_run_named_query_query_level_sqlalchemy_runner_overrides_default(tmp_path):
    add_named_query(tmp_path, "hello_world", "select 'Hello from query runner' as message")
    default_runner = BrokenNamedQueryRunner()
    query_runner = SQLAlchemyNamedQueryRunner(sqlalchemy.create_engine("sqlite+pysqlite:///:memory:"))
    fx = Fluxy(
        "https://ignition.example/system/webdev/Fluxy",
        project_location=tmp_path,
        named_query_runner=default_runner,
    )

    result = fx.db.run_named_query("hello_world", runner=query_runner)

    assert result == [{"message": "Hello from query runner"}]


def test_run_named_query_can_force_gateway_when_sqlalchemy_default_exists(tmp_path):
    add_named_query(tmp_path, "hello_world", "select 'Hello from SQLAlchemy' as message")

    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/runNamedQuery"
        return httpx.Response(200, json={"ok": True, "result": [{"message": "Hello from Gateway"}]})

    fx = Fluxy(
        "https://ignition.example/system/webdev/Fluxy",
        project_location=tmp_path,
        named_query_runner=SQLAlchemyNamedQueryRunner(sqlalchemy.create_engine("sqlite+pysqlite:///:memory:")),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = fx.db.run_named_query("hello_world", use_gateway=True)

    assert result == [{"message": "Hello from Gateway"}]


class BrokenNamedQueryRunner:
    def run_named_query(self, project_location, path, *, parameters=None, project=None):
        raise FluxyError("default runner should not be used")
