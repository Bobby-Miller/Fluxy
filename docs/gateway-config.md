# Gateway Database Test Setup

Fluxy can generate narrow Gateway configuration resources for SQLite and PostgreSQL database connections. The canonical module is `fluxy.gateway_config`.

Use this page to rebuild a database-backed Fluxy integration-test Gateway from zero.

## Assumptions

- You are working from the `fluxy/` package directory.
- Ignition Gateway data lives at `/usr/local/bin/ignition/data`.
- The Flux WebDev project is reachable at `http://localhost:8088/system/webdev/flux`.
- The Gateway has a PostgreSQL JDBC driver configured with driver name `PostgreSQL`.
- The default tag provider is `default`.

Override those values in the commands if your Gateway differs.

## Base Environment

```bash
cd fluxy
export FLUXY_BASE_URL="http://localhost:8088/system/webdev/flux"
export FLUXY_PROJECT_LOCATION="../ignition_flux_project"
export FLUXY_CONFIGURE_BASE_PATH="[default]"
```

Deploy or refresh the WebDev bridge before running live tests:

```bash
uv run python - <<'PY'
import fluxy

fx = fluxy.Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    project_location="../ignition_flux_project",
)
fx.deploy_webdev()
fx.project.request_scan()
PY
```

## SQLite Baseline Datasource

`tests/test_integration_db.py` expects a persistent SQLite connection named `FluxyHello` for the first smoke test. The same test file also creates/removes temporary SQLite datasources through `fx.db.add_datasource(...)`.

Create the local SQLite fixture:

```bash
uv run python - <<'PY'
import sqlite3

connection = sqlite3.connect("hello.sqlite3")
try:
    connection.execute("create table if not exists hello (id integer primary key, message text not null)")
    connection.execute("delete from hello")
    connection.execute("insert into hello (id, message) values (?, ?)", (1, "Hello from SQLite"))
    connection.commit()
finally:
    connection.close()
PY
```

Write the Gateway database-connection resource:

```bash
uv run python -m fluxy.gateway_config \
  /usr/local/bin/ignition/data \
  hello.sqlite3 \
  --connection-name FluxyHello
```

This writes:

```text
/usr/local/bin/ignition/data/udb/hello.sqlite3
/usr/local/bin/ignition/data/config/resources/core/ignition/database-connection/FluxyHello/config.json
/usr/local/bin/ignition/data/config/resources/core/ignition/database-connection/FluxyHello/resource.json
```

The generated connection uses:

```text
driver: SQLite
translator: SQLITE
connectURL: jdbc:sqlite:${data}/udb/hello.sqlite3
```

Restart the Gateway or reload/import Gateway config resources after writing file-backed Gateway config.

Verify SQLite DB coverage:

```bash
uv run pytest tests/test_integration_db.py -rs
```

## PostgreSQL Server

On Arch/Omarchy, install and initialize PostgreSQL:

```bash
sudo pacman -S --needed postgresql
sudo -iu postgres initdb -D /var/lib/postgres/data
sudo systemctl enable --now postgresql
```

If `initdb` reports that the cluster already exists, skip that command and start the service.

Verify PostgreSQL is online:

```bash
systemctl is-active postgresql
pg_isready -h localhost -p 5432
```

Expected:

```text
active
localhost:5432 - accepting connections
```

Create or refresh the Fluxy test role and database:

```bash
if psql -U postgres -tAc "select 1 from pg_roles where rolname = 'fluxy'" | grep -q 1; then
  psql -U postgres -c "ALTER ROLE fluxy WITH LOGIN PASSWORD 'fluxy' CREATEDB"
else
  psql -U postgres -c "CREATE ROLE fluxy LOGIN PASSWORD 'fluxy' CREATEDB"
fi

createdb -U postgres -O fluxy fluxy_test || true
```

If local trust auth is disabled, run the same commands through the `postgres` OS user:

```bash
if sudo -iu postgres psql -tAc "select 1 from pg_roles where rolname = 'fluxy'" | grep -q 1; then
  sudo -iu postgres psql -c "ALTER ROLE fluxy WITH LOGIN PASSWORD 'fluxy' CREATEDB"
else
  sudo -iu postgres psql -c "CREATE ROLE fluxy LOGIN PASSWORD 'fluxy' CREATEDB"
fi

sudo -iu postgres createdb -O fluxy fluxy_test || true
```

Verify the test login:

```bash
PGPASSWORD=fluxy psql -h localhost -U fluxy -d fluxy_test -c "select current_user, current_database(), version()"
```

## PostgreSQL Ignition Datasource

Create a persistent Ignition datasource named `FluxyPostgres` through Fluxy. This uses the same path the API tests exercise: Fluxy WebDev bridge -> `system.db.addDatasource`.

```bash
uv run python - <<'PY'
import fluxy

fx = fluxy.Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    project_location="../ignition_flux_project",
)
fx.deploy_webdev()
fx.project.request_scan()

try:
    fx.db.remove_datasource("FluxyPostgres")
except Exception:
    pass

fx.db.add_datasource(
    "FluxyPostgres",
    "jdbc:postgresql://localhost:5432/fluxy_test",
    jdbc_driver="PostgreSQL",
    description="Persistent Fluxy PostgreSQL datasource",
    username="fluxy",
    password="fluxy",
    validation_query="SELECT 1",
)

print(fx.db.run_scalar_query("select current_database()", database="FluxyPostgres"))
PY
```

Expected output includes:

```text
fluxy_test
```

You can also write a file-backed Gateway config resource for a disposable test datasource. This is useful for config-resource testing, but the live Postgres DB tests create/remove their own datasource through `fx.db.add_datasource(...)`:

```bash
uv run python -m fluxy.gateway_config \
  /usr/local/bin/ignition/data \
  --postgres \
  --host localhost \
  --port 5432 \
  --database fluxy_test \
  --username fluxy \
  --password fluxy
```

This writes:

```text
/usr/local/bin/ignition/data/config/resources/core/ignition/database-connection/FluxyPostgresTestDatasource/config.json
/usr/local/bin/ignition/data/config/resources/core/ignition/database-connection/FluxyPostgresTestDatasource/resource.json
```

The generated connection uses:

```text
driver: PostgreSQL
translator: POSTGRES
connectURL: jdbc:postgresql://localhost:5432/fluxy_test
validationQuery: SELECT 1
```

Verify Postgres DB feature coverage:

```bash
FLUXY_POSTGRES_ENABLED=1 \
FLUXY_POSTGRES_HOST=localhost \
FLUXY_POSTGRES_PORT=5432 \
FLUXY_POSTGRES_DATABASE=fluxy_test \
FLUXY_POSTGRES_USERNAME=fluxy \
FLUXY_POSTGRES_PASSWORD=fluxy \
uv run pytest tests/test_integration_postgres_db.py -rs
```

These tests create/drop `FluxyPostgresTestDatasource` and a temporary PostgreSQL schema. They exercise prepared binds, JSONB, arrays, `generate_series`, `insert ... on conflict ... returning`, `bytea`, and transaction commit/rollback.

## PostgreSQL SQL Historian

Create or verify an Ignition SQL historian provider named `postgresHist` that points at the persistent `FluxyPostgres` datasource.

Expected Gateway resource path:

```text
/usr/local/bin/ignition/data/config/resources/core/com.inductiveautomation.historian/historian-provider/postgresHist/
```

Expected `config.json` shape:

```json
{
  "profile": {
    "type": "SqlHistorian"
  },
  "settings": {
    "database": "FluxyPostgres",
    "partition": {
      "enabled": true,
      "optimized": false,
      "optimizedWindowSeconds": 60,
      "size": 1,
      "sizeUnits": "MONTH"
    },
    "pruning": {
      "age": 1,
      "ageUnits": "YEAR",
      "enabled": false
    },
    "staleMultiplier": 2,
    "trackSce": true
  }
}
```

Restart the Gateway or reload/import Gateway config resources after creating the historian provider.

Verify the SQL historian through Fluxy:

```bash
uv run pytest tests/test_integration_sql_historian.py -rs
```

If the provider name or test tag path differs, set:

```bash
export FLUXY_SQL_HISTORIAN_TEST_PATH_PREFIX="histprov:postgresHist:/sys:gateway:/prov:default:/tag:FluxySqlHistorianIntegration"
```

The SQL historian tests use direct `system.historian.storeDataPoints` writes and validate query-back through `queryAggregatedPoints`. On the current PostgreSQL SQL historian fixture, direct stored points do not mirror Core Historian for `queryRawPoints`, metadata query-back, or annotation query-back.

## Full Database/Historian Verification

Run the database and historian tests after SQLite, PostgreSQL, and `postgresHist` are configured:

```bash
uv run pytest tests/test_integration_db.py -rs

FLUXY_POSTGRES_ENABLED=1 \
FLUXY_POSTGRES_HOST=localhost \
FLUXY_POSTGRES_PORT=5432 \
FLUXY_POSTGRES_DATABASE=fluxy_test \
FLUXY_POSTGRES_USERNAME=fluxy \
FLUXY_POSTGRES_PASSWORD=fluxy \
uv run pytest tests/test_integration_postgres_db.py -rs

uv run pytest tests/test_integration_historian.py tests/test_integration_sql_historian.py -rs
```

## Important Constraints

`fluxy.gateway_config` writes Gateway resources, not project resources. `fx.project.request_scan()` does not reload these resources. Restart the Gateway or use the Gateway UI/config import path when creating file-backed Gateway resources.

Do not edit `data/db/config.idb` directly for this workflow. Ignition 8.3 stores file-backed Gateway config resources under `data/config/resources/`, and direct database edits are a brittle last resort.

The persistent `FluxyPostgres` datasource is intentionally separate from the disposable `FluxyPostgresTestDatasource` used by tests. Do not point the SQL historian at `FluxyPostgresTestDatasource`; the test fixture removes it during cleanup.
