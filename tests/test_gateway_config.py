import json
import sqlite3

import pytest

from fluxy.gateway_config import deploy_postgres_connection, deploy_sqlite_connection


def test_deploy_sqlite_connection_writes_database_connection_resource(tmp_path):
    source_db = tmp_path / "source.sqlite3"
    connection = sqlite3.connect(source_db)
    try:
        connection.execute("create table hello (message text not null)")
        connection.execute("insert into hello (message) values ('Hello')")
        connection.commit()
    finally:
        connection.close()

    written = deploy_sqlite_connection(tmp_path / "gateway-data", source_db)

    gateway_db = tmp_path / "gateway-data" / "udb" / "hello.sqlite3"
    resource_dir = (
        tmp_path
        / "gateway-data"
        / "config"
        / "resources"
        / "core"
        / "ignition"
        / "database-connection"
        / "FluxyHello"
    )
    config = json.loads((resource_dir / "config.json").read_text())
    resource = json.loads((resource_dir / "resource.json").read_text())

    assert gateway_db in written
    assert gateway_db.exists()
    assert config["connectURL"] == "jdbc:sqlite:${data}/udb/hello.sqlite3"
    assert config["driver"] == "SQLite"
    assert config["translator"] == "SQLITE"
    assert resource["attributes"]["enabled"] is True
    assert resource["attributes"]["lastModification"]["actor"] == "fluxy.gateway_config"


def test_deploy_sqlite_connection_rejects_path_traversal(tmp_path):
    source_db = tmp_path / "source.sqlite3"
    source_db.write_bytes(b"")

    with pytest.raises(ValueError, match="Gateway data directory"):
        deploy_sqlite_connection(tmp_path / "gateway-data", source_db, target_relative_path="../hello.sqlite3")


def test_deploy_postgres_connection_writes_database_connection_resource(tmp_path):
    written = deploy_postgres_connection(
        tmp_path / "gateway-data",
        connection_name="FluxyPostgres",
        host="127.0.0.1",
        port=5433,
        database="fluxy_test",
        username="fluxy",
        password="secret",
    )

    resource_dir = (
        tmp_path
        / "gateway-data"
        / "config"
        / "resources"
        / "core"
        / "ignition"
        / "database-connection"
        / "FluxyPostgres"
    )
    config = json.loads((resource_dir / "config.json").read_text())
    resource = json.loads((resource_dir / "resource.json").read_text())

    assert resource_dir / "config.json" in written
    assert resource_dir / "resource.json" in written
    assert config["connectURL"] == "jdbc:postgresql://127.0.0.1:5433/fluxy_test"
    assert config["driver"] == "PostgreSQL"
    assert config["translator"] == "POSTGRES"
    assert config["username"] == "fluxy"
    assert config["password"] == "secret"
    assert config["validationQuery"] == "SELECT 1"
    assert resource["attributes"]["enabled"] is True
    assert resource["attributes"]["lastModification"]["actor"] == "fluxy.gateway_config"
