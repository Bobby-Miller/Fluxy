import os
import sqlite3
import time

import pytest

import fluxy
from fluxy import FluxyError

@pytest.mark.integration
def test_get_connections_and_run_scalar_query_against_fluxy_hello():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    database = os.getenv("FLUXY_DB_NAME", "FluxyHello")

    fx = fluxy.Fluxy(base_url=base_url, token=token)

    try:
        connections = fx.db.get_connections()
        message = fx.db.run_scalar_query(
            "select message from hello where id = ?",
            database=database,
            args=[1],
        )
    except FluxyError as exc:
        pytest.fail("Fluxy database integration failed for %s: %s" % (database, exc))

    matching = [connection for connection in connections if connection.name == database]
    assert matching, "Database connection %s was not reported by system.db.getConnections" % database
    assert matching[0].status == "Valid"
    assert message == "Hello from SQLite"


@pytest.fixture
def fluxy_test_datasource(tmp_path):
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    database = os.getenv("FLUXY_TEST_DATASOURCE_NAME", "FluxyTestDatasource")
    db_path = tmp_path / "test_datasource.sqlite3"
    moved_db_path = tmp_path / "moved.sqlite3"
    connect_url = "jdbc:sqlite:%s" % db_path
    moved_connect_url = "jdbc:sqlite:%s" % moved_db_path
    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)
    create_test_database(db_path, "Hello from added datasource")
    create_test_database(moved_db_path, "Hello from moved datasource")
    create_mixed_type_table(db_path)

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
            description="Fluxy addDatasource/removeDatasource integration test",
        )
        eventually_assert_connection_present(fx, database)
        eventually_read_hello_world(fx, database)
        yield fx, database, moved_connect_url
    finally:
        try:
            if fx.db.remove_datasource(database):
                eventually_assert_datasource_removed(fx, database)
        except FluxyError:
            pass


@pytest.mark.integration
def test_add_read_remove_sqlite_datasource(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    message = fx.db.run_scalar_query(
        "select message from hello where id = ?",
        database=database,
        args=[1],
    )

    assert message == "Hello from added datasource"


@pytest.mark.integration
def test_temporary_datasource_is_reported_by_get_connections(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    connections = fx.db.get_connections()

    assert any(connection.name == database for connection in connections)


@pytest.mark.integration
def test_get_connection_info_for_temporary_datasource(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    info = fx.db.get_connection_info(database)

    assert info
    assert database in [str(value) for value in info.values()] or database in str(info)


@pytest.mark.integration
def test_set_datasource_max_connections_updates_connection_info(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    assert fx.db.set_datasource_max_connections(database, 3)
    info = fx.db.get_connection_info(database)

    assert info
    assert "3" in [str(value) for value in info.values()] or "3" in str(info)


@pytest.mark.integration
def test_run_query_against_temporary_datasource(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    result = fx.db.run_query(
        "select id, message from hello where id = 1",
        database=database,
    )

    assert result == [{"id": 1, "message": "Hello from added datasource"}]
    assert result.columns == ["id", "message"]
    assert result.source == "ignition.dataset"


@pytest.mark.integration
def test_run_prep_query_against_temporary_datasource(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    result = fx.db.run_prep_query(
        "select id, message from hello where id = ?",
        args=[1],
        database=database,
    )

    assert result == [{"id": 1, "message": "Hello from added datasource"}]
    assert result.columns == ["id", "message"]
    assert result.source == "ignition.dataset"


@pytest.mark.integration
def test_run_scalar_prep_query_returns_bound_value(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    value = fx.db.run_scalar_prep_query("select ?", args=["hello World"], database=database)

    assert value == "hello World"


@pytest.mark.integration
def test_run_prep_update_against_temporary_datasource(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    updated = fx.db.run_prep_update(
        "update hello set message = ? where id = ?",
        args=["Hello after prep update", 1],
        database=database,
    )
    result = fx.db.run_prep_query(
        "select message from hello where id = ?",
        args=[1],
        database=database,
    )

    assert updated == 1
    assert result == [{"message": "Hello after prep update"}]


@pytest.mark.integration
def test_run_update_query_against_temporary_datasource(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    updated = fx.db.run_update_query(
        "update hello set message = 'Hello after update query' where id = 1",
        database=database,
    )
    result = fx.db.run_query(
        "select message from hello where id = 1",
        database=database,
    )

    assert updated == 1
    assert result == [{"message": "Hello after update query"}]


@pytest.mark.integration
def test_transaction_rollback_discards_update_query(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource
    tx = fx.db.begin_transaction(database)

    try:
        inserted = fx.db.run_update_query(
            "insert into hello (id, message) values (2, 'rolled back')",
            database=database,
            tx=tx,
        )
        assert inserted == 1
        assert fx.db.rollback_transaction(tx)
    finally:
        try:
            fx.db.close_transaction(tx)
        except FluxyError:
            pass

    result = fx.db.run_query("select message from hello where id = 2", database=database)

    assert result == []


@pytest.mark.integration
def test_transaction_commit_persists_update_query(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource
    tx = fx.db.begin_transaction(database)

    try:
        inserted = fx.db.run_update_query(
            "insert into hello (id, message) values (3, 'committed')",
            database=database,
            tx=tx,
        )
        assert inserted == 1
        assert fx.db.commit_transaction(tx)
    finally:
        try:
            fx.db.close_transaction(tx)
        except FluxyError:
            pass

    result = fx.db.run_query("select message from hello where id = 3", database=database)

    assert result == [{"message": "committed"}]


@pytest.mark.integration
def test_set_datasource_connect_url_switches_database_file(fluxy_test_datasource):
    fx, database, moved_connect_url = fluxy_test_datasource

    assert fx.db.set_datasource_connect_url(database, moved_connect_url)
    message = eventually_read_expected_message(fx, database, "Hello from moved datasource")

    assert message == "Hello from moved datasource"


@pytest.mark.integration
def test_set_datasource_enabled_blocks_and_restores_queries(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    assert fx.db.set_datasource_enabled(database, False)
    eventually_assert_query_fails(fx, database)

    assert fx.db.set_datasource_enabled(database, True)
    message = eventually_read_hello_world(fx, database)

    assert message == "Hello from added datasource"


@pytest.mark.integration
def test_large_mixed_type_query_shapes_and_values(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    rows = fx.db.run_query(
        """
        select id, label, amount, active, optional_text, created_ms, payload_text
        from mixed_values
        order by id
        """,
        database=database,
    )
    filtered = fx.db.run_prep_query(
        """
        select id, label, amount, active, optional_text, created_ms, payload_text
        from mixed_values
        where active = ? and id between ? and ?
        order by id
        """,
        args=[1, 40, 50],
        database=database,
    )
    count = fx.db.run_scalar_query("select count(*) from mixed_values", database=database)
    active_count = fx.db.run_scalar_prep_query(
        "select count(*) from mixed_values where active = ?",
        args=[1],
        database=database,
    )

    assert len(rows) == 256
    assert rows.columns == [
        "id",
        "label",
        "amount",
        "active",
        "optional_text",
        "created_ms",
        "payload_text",
    ]
    assert rows.source == "ignition.dataset"
    assert rows[0] == {
        "id": 1,
        "label": "row-001",
        "amount": 1.25,
        "active": 0,
        "optional_text": "optional-001",
        "created_ms": 1_778_545_001_000,
        "payload_text": '{"row":1,"kind":"odd"}',
    }
    assert rows[6]["optional_text"] is None
    assert rows[-1]["id"] == 256
    assert rows[-1]["label"] == "row-256"
    assert rows[-1]["amount"] == 320.0
    assert rows[-1]["active"] == 1
    assert rows[-1]["created_ms"] == 1_778_545_256_000
    assert [row["id"] for row in filtered] == [40, 42, 44, 46, 48, 50]
    assert count == 256
    assert active_count == 128


@pytest.mark.integration
def test_blob_query_returns_stable_byte_list_payload_shape(fluxy_test_datasource):
    fx, database, _moved_connect_url = fluxy_test_datasource

    rows = fx.db.run_query(
        "select id, payload_blob from mixed_values where id in (1, 2) order by id",
        database=database,
    )

    assert rows.columns == ["id", "payload_blob"]
    assert rows[0]["payload_blob"] == [1, 2, 3]
    assert rows[1]["payload_blob"] == [2, 3, 4]


def create_test_database(path, message):
    connection = sqlite3.connect(path)
    try:
        connection.execute("create table hello (id integer primary key, message text not null)")
        connection.execute("insert into hello (id, message) values (1, ?)", [message])
        connection.commit()
    finally:
        connection.close()


def create_mixed_type_table(path):
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            create table mixed_values (
                id integer primary key,
                label text not null,
                amount real not null,
                active integer not null,
                optional_text text,
                created_ms integer not null,
                payload_text text not null,
                payload_blob blob not null
            )
            """
        )
        rows = [
            (
                index,
                "row-%03d" % index,
                index * 1.25,
                1 if index % 2 == 0 else 0,
                None if index % 7 == 0 else "optional-%03d" % index,
                1_778_545_000_000 + index * 1000,
                '{"row":%d,"kind":"%s"}' % (index, "even" if index % 2 == 0 else "odd"),
                bytes([index % 256, (index + 1) % 256, (index + 2) % 256]),
            )
            for index in range(1, 257)
        ]
        connection.executemany(
            """
            insert into mixed_values
            (id, label, amount, active, optional_text, created_ms, payload_text, payload_blob)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()
    finally:
        connection.close()


def eventually_read_hello_world(fx, database):
    return eventually_read_expected_message(fx, database, "Hello from added datasource")


def eventually_assert_connection_present(fx, database):
    deadline = time.monotonic() + float(os.getenv("FLUXY_DATASOURCE_ADD_TIMEOUT_SECONDS", "12"))
    last_connections = []
    while time.monotonic() < deadline:
        last_connections = fx.db.get_connections()
        if any(connection.name == database for connection in last_connections):
            return
        time.sleep(0.5)
    pytest.fail(
        "Datasource %s was not reported by getConnections: %r"
        % (database, [connection.name for connection in last_connections])
    )


def eventually_read_expected_message(fx, database, expected_message):
    deadline = time.monotonic() + float(os.getenv("FLUXY_DATASOURCE_ADD_TIMEOUT_SECONDS", "12"))
    last_error = None
    last_message = None
    while time.monotonic() < deadline:
        try:
            last_message = fx.db.run_scalar_query(
                "select message from hello where id = ?",
                database=database,
                args=[1],
            )
            if last_message == expected_message:
                return last_message
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Datasource %s did not return %r: last_message=%r last_error=%s"
        % (database, expected_message, last_message, last_error)
    )


def eventually_assert_datasource_removed(fx, database):
    deadline = time.monotonic() + float(os.getenv("FLUXY_DATASOURCE_REMOVE_TIMEOUT_SECONDS", "12"))
    last_value = None
    while time.monotonic() < deadline:
        try:
            last_value = fx.db.run_scalar_query(
                "select message from hello where id = ?",
                database=database,
                args=[1],
            )
        except FluxyError:
            return
        time.sleep(0.5)
    pytest.fail("Datasource %s still queryable after remove: %r" % (database, last_value))


def eventually_assert_query_fails(fx, database):
    deadline = time.monotonic() + float(os.getenv("FLUXY_DATASOURCE_DISABLE_TIMEOUT_SECONDS", "12"))
    last_value = None
    while time.monotonic() < deadline:
        try:
            last_value = fx.db.run_scalar_query(
                "select message from hello where id = ?",
                database=database,
                args=[1],
            )
        except FluxyError:
            return
        time.sleep(0.5)
    pytest.fail("Datasource %s still queryable after disable: %r" % (database, last_value))
