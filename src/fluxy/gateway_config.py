from __future__ import annotations

import argparse
import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_CONNECTION_NAME = "FluxyHello"
DEFAULT_POSTGRES_CONNECTION_NAME = "FluxyPostgresTestDatasource"
DEFAULT_SQLITE_TARGET = Path("udb") / "hello.sqlite3"
CONFIG_RESOURCE_ROOT = Path("config") / "resources" / "core" / "ignition" / "database-connection"


def deploy_sqlite_connection(
    gateway_data_path: str | Path,
    sqlite_path: str | Path,
    *,
    connection_name: str = DEFAULT_CONNECTION_NAME,
    target_relative_path: str | Path = DEFAULT_SQLITE_TARGET,
) -> list[Path]:
    gateway_data_path = Path(gateway_data_path).resolve()
    sqlite_path = Path(sqlite_path).resolve()
    target_relative_path = _safe_relative_path(target_relative_path)

    if not sqlite_path.exists():
        raise FileNotFoundError(sqlite_path)
    if not connection_name.strip():
        raise ValueError("connection_name must not be blank")

    sqlite_target = gateway_data_path / target_relative_path
    sqlite_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sqlite_path, sqlite_target)

    resource_dir = gateway_data_path / CONFIG_RESOURCE_ROOT / connection_name
    resource_dir.mkdir(parents=True, exist_ok=True)

    config_path = resource_dir / "config.json"
    resource_path = resource_dir / "resource.json"
    connect_url = "jdbc:sqlite:${data}/%s" % target_relative_path.as_posix()

    config_path.write_text(json.dumps(sqlite_connection_config(connect_url), indent=2) + "\n", encoding="utf-8")
    resource_path.write_text(
        json.dumps(sqlite_connection_resource(connection_name), indent=2) + "\n",
        encoding="utf-8",
    )
    return [sqlite_target, config_path, resource_path]


def sqlite_connection_config(connect_url: str) -> dict[str, object]:
    return {
        "connectURL": connect_url,
        "connectionProps": "",
        "connectionResetParams": "",
        "defaultTransactionLevel": "DEFAULT",
        "driver": "SQLite",
        "evictionRate": -1,
        "evictionTests": 3,
        "evictionTime": 1800000,
        "failoverMode": "STANDARD",
        "failoverProfile": "",
        "includeSchemaInTableName": False,
        "poolInitSize": 0,
        "poolMaxActive": 8,
        "poolMaxIdle": 8,
        "poolMaxWait": 5000,
        "poolMinIdle": 0,
        "slowQueryLogThreshold": 60000,
        "testOnBorrow": True,
        "testOnReturn": False,
        "testWhileIdle": False,
        "translator": "SQLITE",
        "username": "",
        "validationQuery": "SELECT 1",
        "validationSleepTime": 10000,
    }


def sqlite_connection_resource(connection_name: str) -> dict[str, object]:
    return {
        "scope": "A",
        "description": "Fluxy-managed SQLite test connection.",
        "version": 1,
        "restricted": False,
        "overridable": True,
        "files": ["config.json"],
        "attributes": {
            "lastModification": {
                "actor": "fluxy.gateway_config",
                "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            },
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, "fluxy:database-connection:%s" % connection_name)),
            "enabled": True,
        },
    }


def deploy_postgres_connection(
    gateway_data_path: str | Path,
    *,
    connection_name: str = DEFAULT_POSTGRES_CONNECTION_NAME,
    host: str = "localhost",
    port: int = 5432,
    database: str = "fluxy_test",
    username: str = "fluxy",
    password: str = "fluxy",
) -> list[Path]:
    gateway_data_path = Path(gateway_data_path).resolve()
    if not connection_name.strip():
        raise ValueError("connection_name must not be blank")
    if not host.strip():
        raise ValueError("host must not be blank")
    if not database.strip():
        raise ValueError("database must not be blank")

    resource_dir = gateway_data_path / CONFIG_RESOURCE_ROOT / connection_name
    resource_dir.mkdir(parents=True, exist_ok=True)

    config_path = resource_dir / "config.json"
    resource_path = resource_dir / "resource.json"
    connect_url = "jdbc:postgresql://%s:%s/%s" % (host, int(port), database)

    config_path.write_text(
        json.dumps(
            postgres_connection_config(
                connect_url,
                username=username,
                password=password,
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    resource_path.write_text(
        json.dumps(postgres_connection_resource(connection_name), indent=2) + "\n",
        encoding="utf-8",
    )
    return [config_path, resource_path]


def postgres_connection_config(
    connect_url: str,
    *,
    username: str = "fluxy",
    password: str = "fluxy",
) -> dict[str, object]:
    return {
        "connectURL": connect_url,
        "connectionProps": "",
        "connectionResetParams": "",
        "defaultTransactionLevel": "DEFAULT",
        "driver": "PostgreSQL",
        "evictionRate": -1,
        "evictionTests": 3,
        "evictionTime": 1800000,
        "failoverMode": "STANDARD",
        "failoverProfile": "",
        "includeSchemaInTableName": False,
        "password": password,
        "poolInitSize": 0,
        "poolMaxActive": 8,
        "poolMaxIdle": 8,
        "poolMaxWait": 5000,
        "poolMinIdle": 0,
        "slowQueryLogThreshold": 60000,
        "testOnBorrow": True,
        "testOnReturn": False,
        "testWhileIdle": False,
        "translator": "POSTGRES",
        "username": username,
        "validationQuery": "SELECT 1",
        "validationSleepTime": 10000,
    }


def postgres_connection_resource(connection_name: str) -> dict[str, object]:
    return {
        "scope": "A",
        "description": "Fluxy-managed PostgreSQL test connection.",
        "version": 1,
        "restricted": False,
        "overridable": True,
        "files": ["config.json"],
        "attributes": {
            "lastModification": {
                "actor": "fluxy.gateway_config",
                "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            },
            "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, "fluxy:database-connection:%s" % connection_name)),
            "enabled": True,
        },
    }


def _safe_relative_path(path: str | Path) -> Path:
    relative_path = Path(path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("target_relative_path must stay inside the Gateway data directory")
    return relative_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage Fluxy Gateway configuration resources.")
    parser.add_argument("gateway_data_path", type=Path)
    parser.add_argument("sqlite_path", type=Path, nargs="?")
    parser.add_argument("--connection-name")
    parser.add_argument("--target-relative-path", type=Path, default=DEFAULT_SQLITE_TARGET)
    parser.add_argument("--postgres", action="store_true", help="write a PostgreSQL database connection")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", default="fluxy_test")
    parser.add_argument("--username", default="fluxy")
    parser.add_argument("--password", default="fluxy")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.postgres:
        connection_name = args.connection_name or DEFAULT_POSTGRES_CONNECTION_NAME
        written = deploy_postgres_connection(
            args.gateway_data_path,
            connection_name=connection_name,
            host=args.host,
            port=args.port,
            database=args.database,
            username=args.username,
            password=args.password,
        )
    else:
        if args.sqlite_path is None:
            raise SystemExit("sqlite_path is required unless --postgres is set")
        connection_name = args.connection_name or DEFAULT_CONNECTION_NAME
        written = deploy_sqlite_connection(
            args.gateway_data_path,
            args.sqlite_path,
            connection_name=connection_name,
            target_relative_path=args.target_relative_path,
        )
    print("Wrote %d Gateway config files for database connection %s" % (len(written), connection_name))


if __name__ == "__main__":
    main()
