import os
import time
from uuid import uuid4

import pytest

import fluxy
from fluxy import FluxyError


pytestmark = pytest.mark.integration


def test_postgres_datasource_reports_and_runs_scalar_query(postgres_datasource):
    fx, database, _schema = postgres_datasource

    connections = fx.db.get_connections()
    value = fx.db.run_scalar_query("select 1", database=database)

    assert any(connection.name == database for connection in connections)
    assert value == 1


def test_postgres_prepared_query_update_and_returning(postgres_datasource):
    fx, database, schema = postgres_datasource


    inserted = fx.db.run_prep_update(
        """
        insert into %s.feature_values (label, amount, active, payload)
        values (?, ?::numeric, ?, ?::jsonb)
        """
        % schema,
        args=["alpha", "12.340", True, '{"kind":"prepared","rank":1}'],
        database=database,
    )
    rows = fx.db.run_prep_query(
        """
        select label, amount::text as amount_text, active, payload->>'kind' as payload_kind
        from %s.feature_values
        where label = ?
        """
        % schema,
        args=["alpha"],
        database=database,
    )

    assert inserted == 1
    assert rows == [
        {
            "label": "alpha",
            "amount_text": "12.340",
            "active": True,
            "payload_kind": "prepared",
        }
    ]


def test_postgres_jsonb_array_and_generate_series(postgres_datasource):
    fx, database, schema = postgres_datasource

    rows = fx.db.run_query(
        """
        with generated as (
            select value
            from generate_series(1, 5) as value
        )
        insert into %s.feature_values (label, tags, payload)
        select
            'series-' || value,
            array['fluxy', 'postgres', value::text],
            jsonb_build_object('value', value, 'even', value %% 2 = 0)
        from generated
        returning label, tags[3] as tag_value, (payload->>'even')::boolean as is_even
        """
        % schema,
        database=database,
    )

    assert rows.columns == ["label", "tag_value", "is_even"]
    assert len(rows) == 5
    assert rows[0] == {"label": "series-1", "tag_value": "1", "is_even": False}
    assert rows[1] == {"label": "series-2", "tag_value": "2", "is_even": True}


def test_postgres_upsert_returning_and_bytea_shape(postgres_datasource):
    fx, database, schema = postgres_datasource

    rows = fx.db.run_query(
        """
        insert into %s.feature_values (label, payload_bytes)
        values ('upserted', decode('000102ff', 'hex'))
        on conflict (label)
        do update set payload_bytes = excluded.payload_bytes
        returning label, encode(payload_bytes, 'hex') as payload_hex
        """
        % schema,
        database=database,
    )

    assert rows == [{"label": "upserted", "payload_hex": "000102ff"}]


def test_postgres_transaction_commit_and_rollback(postgres_datasource):
    fx, database, schema = postgres_datasource
    rollback_tx = fx.db.begin_transaction(database)
    try:
        inserted = fx.db.run_update_query(
            "insert into %s.feature_values (label) values ('rolled-back')" % schema,
            database=database,
            tx=rollback_tx,
        )
        assert inserted == 1
        assert fx.db.rollback_transaction(rollback_tx)
    finally:
        try:
            fx.db.close_transaction(rollback_tx)
        except FluxyError:
            pass

    commit_tx = fx.db.begin_transaction(database)
    try:
        inserted = fx.db.run_update_query(
            "insert into %s.feature_values (label) values ('committed')" % schema,
            database=database,
            tx=commit_tx,
        )
        assert inserted == 1
        assert fx.db.commit_transaction(commit_tx)
    finally:
        try:
            fx.db.close_transaction(commit_tx)
        except FluxyError:
            pass

    rows = fx.db.run_query(
        """
        select label
        from %s.feature_values
        where label in ('rolled-back', 'committed')
        order by label
        """
        % schema,
        database=database,
    )

    assert rows == [{"label": "committed"}]


@pytest.fixture
def postgres_datasource():
    if os.getenv("FLUXY_POSTGRES_ENABLED") != "1":
        pytest.skip("Set FLUXY_POSTGRES_ENABLED=1 to run live PostgreSQL integration tests")

    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    database = os.getenv("FLUXY_POSTGRES_DATASOURCE", "FluxyPostgresTestDatasource")
    host = os.getenv("FLUXY_POSTGRES_HOST", "localhost")
    port = os.getenv("FLUXY_POSTGRES_PORT", "5432")
    postgres_database = os.getenv("FLUXY_POSTGRES_DATABASE", "fluxy_test")
    username = os.getenv("FLUXY_POSTGRES_USERNAME", "fluxy")
    password = os.getenv("FLUXY_POSTGRES_PASSWORD", "fluxy")
    jdbc_driver = os.getenv("FLUXY_POSTGRES_JDBC_DRIVER", "PostgreSQL")
    connect_url = "jdbc:postgresql://%s:%s/%s" % (host, port, postgres_database)
    schema = "fluxy_pg_%s" % uuid4().hex[:12]
    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        try:
            fx.db.remove_datasource(database)
        except FluxyError:
            pass
        assert fx.db.add_datasource(
            database,
            connect_url,
            jdbc_driver=jdbc_driver,
            description="Fluxy PostgreSQL integration test datasource",
            username=username,
            password=password,
            validation_query="SELECT 1",
        )
        eventually_assert_postgres_queryable(fx, database)
        create_postgres_fixture_schema(fx, database, schema)
        yield fx, database, schema
    finally:
        try:
            fx.db.run_update_query("drop schema if exists %s cascade" % schema, database=database)
        except FluxyError:
            pass
        try:
            fx.db.remove_datasource(database)
        except FluxyError:
            pass


def create_postgres_fixture_schema(fx, database, schema):
    fx.db.run_update_query("create schema %s" % schema, database=database)
    fx.db.run_update_query(
        """
        create table %s.feature_values (
            id integer generated always as identity primary key,
            label text not null unique,
            amount numeric(12, 3),
            ratio double precision,
            active boolean default false,
            created_at timestamp default current_timestamp,
            created_tz timestamptz default current_timestamp,
            tags text[] default array[]::text[],
            payload jsonb default '{}'::jsonb,
            payload_bytes bytea,
            optional_text text
        )
        """
        % schema,
        database=database,
    )


def eventually_assert_postgres_queryable(fx, database):
    deadline = time.monotonic() + float(os.getenv("FLUXY_POSTGRES_ADD_TIMEOUT_SECONDS", "20"))
    last_error = None
    while time.monotonic() < deadline:
        try:
            if fx.db.run_scalar_query("select 1", database=database) == 1:
                return
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail("PostgreSQL datasource %s did not become queryable: %s" % (database, last_error))
