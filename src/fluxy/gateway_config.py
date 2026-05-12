from __future__ import annotations

import argparse
import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_CONNECTION_NAME = "FluxyHello"
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


def _safe_relative_path(path: str | Path) -> Path:
    relative_path = Path(path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("target_relative_path must stay inside the Gateway data directory")
    return relative_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage Fluxy Gateway configuration resources.")
    parser.add_argument("gateway_data_path", type=Path)
    parser.add_argument("sqlite_path", type=Path)
    parser.add_argument("--connection-name", default=DEFAULT_CONNECTION_NAME)
    parser.add_argument("--target-relative-path", type=Path, default=DEFAULT_SQLITE_TARGET)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    written = deploy_sqlite_connection(
        args.gateway_data_path,
        args.sqlite_path,
        connection_name=args.connection_name,
        target_relative_path=args.target_relative_path,
    )
    print("Wrote %d Gateway config files for database connection %s" % (len(written), args.connection_name))


if __name__ == "__main__":
    main()
