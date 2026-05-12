# User Guide

This guide is the user-facing path for using Fluxy against a local Ignition Gateway.

## Install

```bash
uv sync
```

## Deploy WebDev Bridge

Deploy Fluxy-owned WebDev endpoints into the Ignition project filesystem:

```bash
uv run python -m fluxy.deploy_webdev ../ignition_flux_project
```

Reload the Ignition project resources:

```python
from fluxy import Fluxy

fx = Fluxy(base_url="http://localhost:8088/system/webdev/flux")
fx.project.request_scan()
```

## Use Tags

```python
from fluxy import Fluxy

fx = Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    tag_provider="default",
)

quality = fx.tag.write_blocking("[default]FluxyGuide/Example", "hello")
value = fx.tag.read_blocking("[default]FluxyGuide/Example")
print(quality.quality, value.value, value.quality)
```

Use `fx.tag.configure(...)` before that example if the tag does not already exist.

## Deploy Script Functions

Deploy the bundled `hello_world.py` function file into the Ignition project:

```python
from fluxy import Fluxy

fx = Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    project_location="../ignition_flux_project",
)

fx.scripting.deploy_function_file("hello_world.py", target_directory="scratch")
fx.project.request_scan()
result = fx.scripting.run_function_file("hello_world.py", target_directory="scratch")
print(result.result)
fx.scripting.delete_function_file("hello_world.py", target_directory="scratch")
fx.project.request_scan()
```

## Configure SQLite Gateway Connection

Create a local SQLite database:

```bash
uv run python - <<'PY'
import sqlite3

connection = sqlite3.connect("hello.sqlite3")
try:
    connection.execute("create table if not exists hello (id integer primary key, message text not null)")
    connection.execute("delete from hello")
    connection.execute("insert into hello (message) values (?)", ("Hello from SQLite",))
    connection.commit()
finally:
    connection.close()
PY
```

Deploy the Gateway database connection resource:

```bash
uv run python -m fluxy.gateway_config \
  /usr/local/bin/ignition/data \
  hello.sqlite3 \
  --connection-name FluxyHello
```

Restart the Gateway so Ignition loads the new database connection:

```bash
/usr/local/bin/ignition/gwcmd.sh --restart --promptyes
```

After restart, `FluxyHello` should appear in the Gateway database connections menu with status `Valid`.

Query through Fluxy:

```python
from fluxy import Fluxy

fx = Fluxy(base_url="http://localhost:8088/system/webdev/flux")

connections = fx.db.get_connections()
print([(connection.name, connection.status) for connection in connections])

message = fx.db.run_scalar_query(
    "select message from hello where id = ?",
    database="FluxyHello",
    args=[1],
)
print(message)
```

## Add And Run Named Query

Create a project named query resource that uses the `FluxyHello` database connection:

```python
from fluxy import Fluxy

fx = Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    project_location="../ignition_flux_project",
)

fx.named_query.add_named_query(
    "hello_world",
    "select message from hello where id = 1",
    database="FluxyHello",
)
fx.project.request_scan()

rows = fx.db.run_named_query("hello_world")
print(rows)

fx.named_query.delete_named_query("hello_world")
fx.project.request_scan()
```

Named query deletion may unload asynchronously after the scan; integration tests poll briefly before asserting the deleted query no longer runs.

## Run Named Queries With SQLAlchemy

`fx.db.run_named_query(...)` can optionally run through SQLAlchemy instead of the Ignition Gateway. This is a plugin path: SQLAlchemy is not a core Fluxy dependency.

Install the optional dependency group for local development or tests:

```bash
uv sync --group sqlalchemy
```

Configure SQLAlchemy as the default named-query runner for one `Fluxy` instance:

```python
from sqlalchemy import create_engine

from fluxy import Fluxy
from fluxy.plugins.sqlalchemy import SQLAlchemyNamedQueryRunner

engine = create_engine("sqlite+pysqlite:///hello.sqlite3")
runner = SQLAlchemyNamedQueryRunner(engine)

fx = Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    project_location="../ignition_flux_project",
    named_query_runner=runner,
)

rows = fx.db.run_named_query("hello_world")
```

The SQLAlchemy plugin reads the Ignition named-query SQL from the project filesystem:

```text
ignition/named-query/<query_name>/query.sql
```

Use a query-level runner to override the instance default for one call:

```python
rows = fx.db.run_named_query("hello_world", runner=runner)
```

Force the Gateway path even when the `Fluxy` instance has a SQLAlchemy runner configured:

```python
rows = fx.db.run_named_query("hello_world", use_gateway=True)
```

Both Gateway and SQLAlchemy paths return `QueryResult`, so user code can consume the same row-mapping shape either way. The `source` field tells which runner produced the result:

```python
rows = fx.db.run_named_query("hello_world")
print(rows.source)  # "sqlalchemy" or "ignition.dataset"
```

## Dataset Results

Ignition database APIs often return a Dataset, while Python database libraries such as SQLAlchemy return row mapping objects. Fluxy standardizes dataset-like results at the Python interface so callers can use one shape no matter where the data came from.

The rule for any Fluxy API that returns tabular data is:

- Ignition WebDev should do the smallest safe serialization step: convert the Dataset into `columns + rows`.
- Fluxy Python should convert `columns + rows` into row mappings.
- User-facing code should receive `QueryResult`, which behaves like `list[dict[str, Any]]` and carries boundary metadata.

Gateway wire shape:

```json
{
  "columns": ["id", "message"],
  "rows": [
    [1, "Hello from SQLite"],
    [2, "Hello from SQLite"]
  ]
}
```

Python-facing shape:

```python
rows = fx.db.run_named_query("multi_row")

assert rows == [
    {"id": 1, "message": "Hello from SQLite"},
    {"id": 2, "message": "Hello from SQLite"},
]
assert rows.columns == ["id", "message"]
```

`QueryResult` also explains the boundary conversion:

```python
assert rows.source == "ignition.dataset"
assert rows.message == "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings"
```

The SQLAlchemy named-query plugin returns the same object shape:

```python
assert rows.source == "sqlalchemy"
assert rows.mappings() is rows
```

Future Fluxy features that expose Ignition Datasets should follow this model rather than building dictionaries in Gateway script code. Keep Ignition focused on accessing Ignition-only APIs and serializing minimal data; keep Python responsible for ergonomic result objects.

## Run Tests

Local tests:

```bash
uv run pytest -q
uv run ruff check .
```

Live integration tests are opt-in. See `integration-tests.md` for environment flags.
