# API

Create a `Fluxy` instance:

```python
from fluxy import Fluxy

fx = Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    project_location="/usr/local/bin/ignition/data/projects/flux",
    tag_provider="default",
)
```

`project_location` is optional, but required for operations that modify project files.

`tag_provider` is optional, but used as the default base path for tag-provider modifying operations such as `tag.configure(...)` when `base_path` is omitted.

## Tags

Read one tag:

```python
value = fx.tag.read_blocking("[default]FluxyIntegration/StringTag")
```

Read many tags:

```python
values = fx.tag.read_blocking([
    "[default]FluxyIntegration/StringTag",
    "[default]FluxyIntegration/FloatTag",
])
```

Write one tag:

```python
quality = fx.tag.write_blocking("[default]FluxyIntegration/StringTag", "hello")
```

Write many tags:

```python
qualities = fx.tag.write_blocking(
    ["[default]FluxyIntegration/IntegerTag", "[default]FluxyIntegration/FloatTag"],
    [1, 6.7],
)
```

Delete tags:

```python
qualities = fx.tag.delete_tags([
    "[default]FluxyIntegration/IntegerTag",
    "[default]FluxyIntegration/FloatTag",
])
```

Forbidden tag APIs:

`system.tag.exists` is intentionally not implemented and should stay forbidden. Use `read_blocking(...)` and monitor the returned quality for `Bad_DoesNotExist` when a workflow needs to prove whether a tag is missing. This is more performant because it avoids adding a dedicated gateway call and reuses the normal tag-read path.

Copy one tag or a list of tags into a destination folder:

```python
result = fx.tag.copy(
    "[default]FluxyIntegration/StringTag",
    "[default]FluxyIntegration/Copies",
)
```

Move a tag:

```python
result = fx.tag.move(
    "[default]FluxyIntegration/Source/MoveOriginalTag",
    "[default]FluxyIntegration/Destination",
)
```

The move destination is the destination folder, matching `system.tag.move(tags, destination, collisionPolicy)`.

Rename a tag:

```python
result = fx.tag.rename("[default]FluxyIntegration/RenameOriginalTag", "RenameNewTag")
```

Export tags:

```python
exported = fx.tag.export_tags("[default]FluxyIntegration")
print(exported.raw_json)
```

Import tags from a decoded Ignition export payload:

```python
results = fx.tag.import_tags(exported.tags, base_path="[default]", collision_policy="o")
```

Get tag configuration:

```python
configs = fx.tag.get_configuration("[default]FluxyIntegration/StringTag")
assert configs[0]["documentation"] == "Hello Description"
```

Configure tags:

```python
results = fx.tag.configure(
    [
        {
            "name": "FluxyIntegration",
            "tagType": "Folder",
            "tags": [
                {
                    "name": "StringTag",
                    "tagType": "AtomicTag",
                    "valueSource": "memory",
                    "dataType": "String",
                    "value": "hello",
                }
            ],
        }
    ],
    base_path="[default]",
    collision_policy="o",
)
```

If `tag_provider="default"` was configured on the `Fluxy` instance, `base_path` may be omitted:

```python
results = fx.tag.configure([{"name": "Folder", "tagType": "Folder"}])
```

Browse tags:

```python
results = fx.tag.browse("[default]FluxyIntegration")
```

Query tags through `system.tag.query`:

```python
results = fx.tag.query(
    "default",
    query={"condition": {"path": "*StringTag*"}},
    limit=100,
)
for result in results:
    print(result.get("fullPath") or result.get("path"))
print(results.continuation_point)
```

## Devices

List configured devices:

```python
devices = fx.device.list_devices()
for device in devices:
    print(device.name, device.enabled, device.state, device.driver)
```

Add, disable, and remove a disposable simulator device:

```python
fx.device.add_device(
    "Simulator",
    "FluxyTemporarySimulator",
    device_props={"Enabled": 0},
    description="Fluxy disposable integration test device",
)
fx.device.set_device_enabled("FluxyTemporarySimulator", False)
fx.device.remove_device("FluxyTemporarySimulator")
```

Only device APIs with closed-loop tests are exposed. `system.device.getDeviceHostname`, `refreshBrowse`, and `restart` are intentionally not wrapped yet.

## Database

List database connections:

```python
connections = fx.db.get_connections()
for connection in connections:
    print(connection.name, connection.status)
```

Inspect one datasource:

```python
info = fx.db.get_connection_info("FluxyTestDatasource")
```

Add and remove an Ignition datasource:

```python
fx.db.add_datasource(
    "FluxyTestDatasource",
    "jdbc:sqlite:/tmp/test_datasource.sqlite3",
    jdbc_driver="SQLite",
    validation_query="SELECT 1",
)
fx.db.set_datasource_connect_url(
    "FluxyTestDatasource",
    "jdbc:sqlite:/tmp/other_test_datasource.sqlite3",
)
fx.db.set_datasource_enabled("FluxyTestDatasource", True)
fx.db.set_datasource_max_connections("FluxyTestDatasource", 4)
fx.db.remove_datasource("FluxyTestDatasource")
```

Run unprepared and prepared queries:

```python
rows = fx.db.run_query("select id, message from hello", database="FluxyHello")
rows = fx.db.run_prep_query(
    "select id, message from hello where id = ?",
    args=[1],
    database="FluxyHello",
)
message = fx.db.run_scalar_prep_query(
    "select message from hello where id = ?",
    args=[1],
    database="FluxyHello",
)
```

Run updates and transactions:

```python
tx = fx.db.begin_transaction("FluxyHello")
try:
    fx.db.run_update_query(
        "insert into hello(message) values ('from transaction')",
        database="FluxyHello",
        tx=tx,
    )
    fx.db.commit_transaction(tx)
finally:
    fx.db.close_transaction(tx)
```

Rollback uses the transaction id returned by `begin_transaction(...)`:

```python
tx = fx.db.begin_transaction("FluxyHello")
try:
    fx.db.run_update_query(
        "update hello set message = 'rolled back' where id = 1",
        database="FluxyHello",
        tx=tx,
    )
    fx.db.rollback_transaction(tx)
finally:
    fx.db.close_transaction(tx)
```

Run a scalar query:

```python
message = fx.db.run_scalar_query(
    "select message from hello where id = ?",
    database="FluxyHello",
    args=[1],
)
assert message == "Hello from SQLite"
```

Run a named query:

```python
rows = fx.db.run_named_query("hello_world")
assert rows == [{"message": "Hello from SQLite"}]
```

`run_named_query(...)` returns `QueryResult`, a `list[dict[str, Any]]` subclass that behaves like SQLAlchemy-style row mappings. Multi-row datasets preserve row order:

```python
rows = fx.db.run_named_query("multi_row")
assert rows == [
    {"id": 1, "message": "first"},
    {"id": 2, "message": "second"},
]
assert rows.columns == ["id", "message"]
```

Ignition returns a Dataset at the Gateway boundary. Fluxy keeps the Gateway WebDev work small by serializing that Dataset as `columns + rows`, then the Python client converts it into `QueryResult` row mappings. The interface metadata makes that boundary visible:

```python
rows = fx.db.run_named_query("multi_row")
assert rows.source == "ignition.dataset"
assert rows.message == "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings"
```

See `docs/user-guide.md#dataset-results` for the project-wide rule: any Fluxy API that exposes an Ignition Dataset should use this Dataset-to-`QueryResult` boundary model.

Live DB integration tests exercise larger SQLite result sets with 256 rows and mixed column types. Observed shape: integer, real, text, and null values preserve their JSON equivalents; SQLite boolean-like columns return `0`/`1`; epoch millisecond columns remain integers; BLOB columns return byte-value lists such as `[1, 2, 3]`.

Run named queries through an optional SQLAlchemy plugin instead of the Ignition Gateway:

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

rows = fx.db.run_named_query("hello_world", parameters={"world": "Hello"})
```

The plugin reads `ignition/named-query/<name>/query.sql` from `project_location` and executes it directly against the SQLAlchemy engine. SQLAlchemy is not a core Fluxy dependency; install it in development with:

```bash
uv sync --group sqlalchemy
uv run --group sqlalchemy pytest tests/test_sqlalchemy_plugin.py
```

Override the default runner for one call, or force the Gateway route:

```python
rows = fx.db.run_named_query("hello_world", runner=other_runner)
rows = fx.db.run_named_query("hello_world", use_gateway=True)
```

## Project

Request a project scan and inspect project context:

```python
result = fx.project.request_scan()
project_name = fx.project.get_project_name()
project_names = fx.project.get_project_names()
assert project_name in project_names
```

## Historian

Inject and query raw points through Ignition 8.3 `system.historian`:

```python
path = "histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration/Test"
qualities = fx.historian.store_data_points(
    [path, path],
    [12.5, 13.5],
    timestamps=[1778545000000, 1778545001000],
    qualities=[192, 192],
)
rows = fx.historian.query_raw_points(
    [path],
    start_time=1778544990000,
    end_time=1778545010000,
)
aggregated = fx.historian.query_aggregated_points(
    [path],
    start_time=1778544990000,
    end_time=1778545010000,
    aggregates=["Maximum"],
    column_names=["value"],
)
browse_results = fx.historian.browse(
    "histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration"
)
metadata_qualities = fx.historian.store_metadata(
    [path], [1778545000000], {"documentation": "checked", "engUnit": "flux"}
)
metadata = fx.historian.query_metadata([path], start_date=1778544990000, end_date=1778545010000)
qualities = fx.historian.store_annotations(
    [path], [1778544995000], end_times=[1778545005000], types=["note"], data=["checked"]
)
annotations = fx.historian.query_annotations([path], 1778544990000, end_date=1778545010000)
fx.historian.delete_annotations([path], [annotations[0].storage_id])
```

The WebDev bridge checks `system.util.getVersion()` before selecting historian functions. Ignition 8.3+ uses `system.historian.browse`, `storeDataPoints`, and `queryRawPoints`; Ignition 8.1 falls back to `system.tag.browseHistoricalTags`, `storeTagHistory`, and `queryTagHistory`. Prefer 8.3 historical path layout (`histprov:...:/sys:...:/prov:...:/tag:...`) in Python callers; the 8.1 storage fallback parses that layout into the legacy `historyprovider + tagprovider + relative tag path` call shape.

The closed-loop tests store a unique path, browse the parent historian path until the unique child appears, query raw and aggregated points back, store/query metadata, store/query/delete a unique annotation, and verify deletion. They require a configured `Core Historian` provider on 8.3. Use `FLUXY_HISTORIAN_TEST_PATH_PREFIX` if the provider, gateway, or tag-provider path differs.

Datatype boundary from live tag-to-history tests: `Boolean` round-trips as `1.0`/`0.0`; integer and float memory tags round-trip as numeric values; `DateTime` can be stored as epoch milliseconds and queries back numerically; `String` can return a Good store quality but does not query back through `queryRawPoints` in the Core Historian fixture; `Document` is rejected by `storeDataPoints`.

## Util

Gateway diagnostics:

```python
version = fx.util.get_version()
modules = fx.util.get_modules()
status = fx.util.get_gateway_status("localhost:8088")
project_name = fx.util.get_project_name()
```

`get_version()` is cached after the first gateway call. Use `fx.util.get_version(refresh=True)` or `fx.util.refresh_version()` after a gateway upgrade/restart if you need to force a fresh version read.

Write and query an audit event through a configured audit profile:

```python
fx.util.audit(
    "FluxyIntegrationAudit",
    action_target="unique-target",
    action_value="created",
    audit_profile="Audit",
    actor="fluxy",
)
rows = fx.util.query_audit_log(
    "Audit",
    action_filter="FluxyIntegrationAudit",
    target_filter="unique-target",
)
```

The closed-loop test defaults to audit profile `Audit`; set `FLUXY_AUDIT_PROFILE` if your profile has another name.

## Reports

List and execute reports:

```python
project = fx.project.get_project_name()
reports = fx.report.get_report_names_as_list(project)
report_rows = fx.report.get_report_names_as_dataset(project)
pdf = fx.report.execute_report("test_Report", project, file_type="pdf")
```

`execute_report(...)` returns `ReportExecutionResult` with raw `content` bytes and the returned `file_type`. The closed-loop test expects the configured report fixture to render a PDF.

## Users

Create and clean up a disposable role and user:

```python
fx.user.add_role("UserDB", "fluxy_role")
fx.user.edit_role("UserDB", "fluxy_role", "fluxy_role_edited")
fx.user.add_user(
    "UserDB",
    "fluxy_user",
    "password",
    fields={"firstname": "Fluxy"},
    roles=["fluxy_role"],
)
user = fx.user.get_user("UserDB", "fluxy_user")
fx.user.edit_user("UserDB", "fluxy_user", fields={"firstname": "FluxyEdited"})
fx.user.remove_user("UserDB", "fluxy_user")
fx.user.remove_role("UserDB", "fluxy_role_edited")
fx.user.add_schedule("fluxy_schedule", source_schedule="Always")
schedule = fx.user.get_schedule("fluxy_schedule")
fx.user.remove_schedule("fluxy_schedule")
fx.user.add_holiday("fluxy_holiday", 2114904400000, repeat_annually=False)
holiday = fx.user.get_holiday("fluxy_holiday")
fx.user.remove_holiday("fluxy_holiday")
```

The closed-loop tests default to `userDB` and resolve source names case-insensitively, so `UserDB` works. Schedule and holiday APIs create global gateway resources with unique disposable names and remove them after verification.

## Alarms

Query active alarms and manage shelving:

```python
source = "prov:default:/tag:FluxyAlarmIntegration/AlarmFloat:/alm:HighAlarm"
rows = fx.alarm.query_status(source=[source], include_shelved=True)
fx.alarm.shelve([source], timeout_seconds=60)
shelved = fx.alarm.get_shelved_paths()
fx.alarm.unshelve([source])
```

Acknowledge alarm events by `EventId` returned from `query_status(...)`:

```python
failed = fx.alarm.acknowledge(["event-id"], notes="Checked by Fluxy", username="fluxy")
```

The closed-loop test creates a disposable memory tag with a high alarm, writes an active value, queries alarm status, shelves and unshelves the alarm source, optionally acknowledges returned event ids, then deletes the tag folder.

## OPC

Browse and interact with an OPC server:

```python
server = "Ignition OPC UA Server"
servers = fx.opc.get_servers(include_disabled=True)
state = fx.opc.get_server_state(server)
rows = fx.opc.browse(opc_server=server, device="FluxyOpcSimulator")
device_nodes = fx.opc.browse_server(server, "Devices")
simple_rows = fx.opc.browse_simple(opc_server=server, device="FluxyOpcSimulator")
item_path = rows[0]["opcItemPath"]
value = fx.opc.read_value(server, item_path)
values = fx.opc.read_values(server, [item_path])
quality = fx.opc.write_value(server, item_path, 123)
qualities = fx.opc.write_values(server, [item_path], [124])
```

The closed-loop test creates a disposable simulator device, verifies the Ignition OPC UA server is connected, browses through `browse`, `browseServer`, and `browseSimple`, reads values, writes to a writable node, reads it back, and removes the device.

## Named Queries

Observed Ignition named query parameter `sqlType` values are available as `NAMED_QUERY_SQL_TYPES` in `fluxy.named_query`:

| Type | sqlType |
| --- | ---: |
| Int1 | 0 |
| Int2 | 1 |
| Int4 | 2 |
| Int8 | 3 |
| Float4 | 4 |
| Float8 | 5 |
| Boolean | 6 |
| String | 7 |
| DateTime | 8 |
| ByteArray | 20 |

Add a project named query resource:

```python
fx.named_query.add_named_query(
    "hello_world",
    "select message from hello where id = 1",
    database="FluxyHello",
)
fx.project.request_scan()
```

Delete a project named query resource:

```python
fx.named_query.delete_named_query("hello_world")
fx.project.request_scan()
```

Named query deletion can unload asynchronously after `request_scan()`. Tests should poll briefly instead of assuming immediate failure from `system.db.runNamedQuery`.

## Scripting

Run a deployed project script function file:

```python
result = fx.scripting.run_function_file("hello_world.py")
assert result.result == "Hello World!"
```

Deploy a function file into the configured `project_location`:

```python
fx.scripting.deploy_function_file("hello_world.py")
fx.project.request_scan()
```

Deploy and run a function file under a target directory:

```python
fx.scripting.deploy_function_file("hello_world.py", target_directory="scratch")
fx.project.request_scan()
result = fx.scripting.run_function_file("hello_world.py", target_directory="scratch")
```

Delete a deployed function file resource:

```python
fx.scripting.delete_function_file("hello_world.py", target_directory="scratch")
fx.project.request_scan()
```

This endpoint executes code inside Ignition. Only deploy and enable it in controlled development environments.
