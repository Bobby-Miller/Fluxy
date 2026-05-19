# fluxy

A Python library that emulates useful subsets of Ignition's `system` APIs from outside Ignition.

Install as a library:

```bash
uv add fluxy-ign
```

Install as a deployment tool:

```bash
uv tool install fluxy-ign
```

Install with MCP support:

```bash
uv tool install 'fluxy-ign[mcp]'
```

Authenticated WebDev deployment:

```bash
fluxy-deploy-webdev /path/to/ignition/data/projects/flux \
  --auth-token-file /path/to/fluxy-token
```

Clients must pass the same bearer token:

```python
fx = Fluxy("http://localhost:8088/system/webdev/flux", token="shared-secret-token")
```

See `docs/auth.md` for the full auth workflow, including token creation, project scan, client configuration, and troubleshooting `401`/`403` responses.

Run the optional MCP adapter:

```bash
fluxy-mcp \
  --base-url http://localhost:8088/system/webdev/flux \
  --token-file /path/to/fluxy-token
```

The MCP server is read-only by default. Add `--allow-writes` to expose write/configure tools and `--allow-destructive` to expose destructive tools such as tag deletion.

The PyPI distribution is `fluxy-ign`; the Python import remains `fluxy`.

Start with `docs/user-guide.md` for the user workflow. See `docs/` for architecture, deployment, API, Gateway config, and integration-test details.

Initial scope:

- `fx.tag.read_blocking(tag_paths)`
- `fx.tag.write_blocking(tag_paths, values)`
- `fx.tag.copy(tag_paths, destination_path)`
- `fx.tag.configure(tags, base_path=None, collision_policy="o")`
- `fx.tag.browse(path=None, tag_filter=None)`
- `fx.tag.query(provider, query=None, limit=None, continuation=None)`
- `fx.alarm` helpers for tested disposable alarm query/shelve/unshelve/acknowledge workflows
- `fx.db` helpers for Ignition datasource management, SQL queries, prepared queries, updates, transactions, and named queries
- `fx.device` helpers for tested Ignition simulator-device add/list/enable/remove workflows
- `fx.historian` helpers for tested `Core Historian` browse and raw point injection/query workflows
- `fx.opc` helpers for tested disposable simulator-device OPC browse/read/write workflows
- `fx.report` helpers for tested report listing/execution workflows
- `fx.user` helpers for tested disposable user/role workflows against `userDB`
- `fx.util` helpers for tested gateway diagnostics and audit write/query workflows
- `fx.project.request_scan()`
- `python -m fluxy.gateway_config` for narrow Gateway SQLite/PostgreSQL connection resource deployment
- `fluxy-mcp` optional MCP server over the Fluxy API, read-only by default
- HTTP bridge to Ignition WebDev endpoints that call the real `system.tag`, tested `system.alarm`, `system.db`, tested `system.device`, tested `system.historian`, tested `system.opc`, and tested `system.util` APIs inside the gateway.

Snake_case is canonical for Python code. Ignition-style aliases are available for porting scripts:

- `fx.tag.readBlocking(...)`
- `fx.tag.writeBlocking(...)`
- `fx.project.requestScan()`

## Python Usage

```python
from fluxy import Fluxy

fx = Fluxy(
    base_url="https://ignition.example.com/system/webdev/<webdev-project>",
    project_location="/usr/local/bin/ignition/data/projects/flux",
    tag_provider="default",
    token="shared-secret-token",
)

values = fx.tag.read_blocking([
    "[default]Path/To/Tag1",
    "[default]Path/To/Tag2",
])

for value in values:
    print(value.tag_path, value.value, value.quality, value.timestamp)
```

Single-tag reads also work and return a single `QualifiedValue`:

```python
value = fx.tag.read_blocking("[default]Path/To/Tag1")
```

Write/readback shape:

```python
tag_paths = [
    "[Tag_02]WY/AL/PADS/AL01-16/AL01-16_RTU_35/WELL/Well_01/LOAD_FACTOR",
]

qualities = fx.tag.write_blocking(tag_paths, [1.1])
values = fx.tag.read_blocking(tag_paths)
```

Single-tag writes also work and return a single `WriteResult`:

```python
quality = fx.tag.write_blocking("[default]Path/To/Setpoint", 12.3)
```

Configure shape:

```python
qualities = fx.tag.configure(
    [
        {
            "name": "MemoryFloat",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Float4",
            "value": 1.0,
        }
    ],
    base_path="[default]Folder",
    collision_policy="o",
)
```

Browse shape:

```python
results = fx.tag.browse("[default]Folder")
for result in results:
    print(result.name, result.full_path, result.tag_type, result.data_type)
```

Tag discovery shape:

```python
missing = fx.tag.read_blocking("[default]Folder/MissingTag")
if str(missing.quality).startswith("Bad_DoesNotExist"):
    print("tag is missing")

fx.tag.copy("[default]Folder/MemoryFloat", "[default]Folder/Copies")

results = fx.tag.query("default", query={"condition": {"path": "*MemoryFloat*"}})
```

`system.tag.exists` is forbidden in Fluxy. Use `read_blocking(...)` and monitor for `Bad_DoesNotExist` instead; it is more performant because it stays on the normal tag-read path instead of adding a dedicated gateway call.

Alarm shape:

```python
source = "prov:default:/tag:FluxyAlarmIntegration/AlarmFloat:/alm:HighAlarm"
rows = fx.alarm.query_status(source=[source], include_shelved=True)
fx.alarm.shelve([source], timeout_seconds=60)
shelved = fx.alarm.get_shelved_paths()
fx.alarm.unshelve([source])
```

Dataset-like database results return `QueryResult`, a `list[dict[str, Any]]` subclass with boundary metadata. Ignition Datasets are serialized as `columns + rows` by WebDev and converted to row mappings in Python. See `docs/user-guide.md#dataset-results`.

Live DB tests cover 256-row mixed SQLite datasets. Integers/reals/text/nulls preserve JSON-compatible values, SQLite boolean-like values return `0`/`1`, epoch milliseconds remain integers, and BLOBs return byte-value lists.

Device management shape:

```python
fx.device.add_device("Simulator", "FluxyTemporarySimulator", {"Enabled": 0})
devices = fx.device.list_devices()
fx.device.set_device_enabled("FluxyTemporarySimulator", False)
fx.device.remove_device("FluxyTemporarySimulator")
```

Historian shape:

```python
path = "histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration/Test"
fx.historian.store_data_points([path], [12.5], [1778545000000], [192])
rows = fx.historian.query_raw_points([path], 1778544990000, 1778545010000)
aggregated = fx.historian.query_aggregated_points(
    [path],
    1778544990000,
    1778545010000,
    aggregates=["Maximum"],
    column_names=["value"],
)
browse_results = fx.historian.browse(
    "histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration"
)
fx.historian.store_metadata([path], [1778545000000], {"documentation": "checked"})
metadata = fx.historian.query_metadata([path], start_date=1778544990000, end_date=1778545010000)
qualities = fx.historian.store_annotations(
    [path], [1778544995000], end_times=[1778545005000], types=["note"], data=["checked"]
)
annotations = fx.historian.query_annotations([path], 1778544990000, end_date=1778545010000)
fx.historian.delete_annotations([path], [annotations[0].storage_id])
```

The historian WebDev bridge selects `system.historian.*` on Ignition 8.3+ and falls back to the 8.1 `system.tag.*` historian functions when needed. Prefer 8.3 `sys`/`prov` historical paths in Python; the 8.1 storage fallback maps them to legacy `storeTagHistory` arguments.

Live tag-to-history boundary tests show Core Historian raw data points are numeric-oriented: Boolean stores as `1.0`/`0.0`, numeric tags round-trip numerically, DateTime stores as epoch milliseconds, String does not query back through `queryRawPoints` despite a Good store quality, and Document is rejected by `storeDataPoints`.

OPC shape:

```python
server = "Ignition OPC UA Server"
servers = fx.opc.get_servers(include_disabled=True)
rows = fx.opc.browse(opc_server=server, device="FluxyOpcSimulator")
device_nodes = fx.opc.browse_server(server, "Devices")
simple_rows = fx.opc.browse_simple(opc_server=server, device="FluxyOpcSimulator")
value = fx.opc.read_value(server, rows[0]["opcItemPath"])
quality = fx.opc.write_value(server, rows[0]["opcItemPath"], 123)
```

Util diagnostics and audit shape:

```python
version = fx.util.get_version()
modules = fx.util.get_modules()
fx.util.audit("FluxyIntegrationAudit", action_target="unique", audit_profile="Audit")
rows = fx.util.query_audit_log("Audit", action_filter="FluxyIntegrationAudit")
```

`fx.util.get_version()` is cached after the first gateway read. Use `fx.util.refresh_version()` after changing gateway versions.

Report shape:

```python
project = fx.project.get_project_name()
reports = fx.report.get_report_names_as_list(project)
report_rows = fx.report.get_report_names_as_dataset(project)
pdf = fx.report.execute_report("test_Report", project, file_type="pdf")
```

User source shape:

```python
sources = fx.user.get_user_sources()
fx.user.add_role("UserDB", "fluxy_role")
fx.user.edit_role("UserDB", "fluxy_role", "fluxy_role_edited")
fx.user.add_user("UserDB", "fluxy_user", "password", roles=["fluxy_role"])
user = fx.user.get_user("UserDB", "fluxy_user")
fx.user.remove_user("UserDB", "fluxy_user")
fx.user.remove_role("UserDB", "fluxy_role_edited")
fx.user.add_schedule("fluxy_schedule", source_schedule="Always")
fx.user.remove_schedule("fluxy_schedule")
fx.user.add_holiday("fluxy_holiday", 2114904400000)
fx.user.remove_holiday("fluxy_holiday")
```

Project scan shape:

```python
result = fx.project.request_scan()
print(result.ok, result.message)
```

## WebDev Contract

Read request:

```json
{
  "tagPaths": ["[default]Path/To/Tag"],
  "timeoutMs": 45000
}
```

`tagPaths` is the canonical request key. The Ignition WebDev bridge also accepts `tag_paths` and `tag_list` as compatibility aliases for existing generated files.

Configure request:

```json
{
  "basePath": "[default]Folder",
  "tags": [
    {
      "name": "MemoryFloat",
      "tagType": "AtomicTag",
      "valueSource": "memory",
      "dataType": "Float4",
      "value": 1.0
    }
  ],
  "collisionPolicy": "o"
}
```

Read response:

```json
{
  "ok": true,
  "values": [
    {
      "tagPath": "[default]Path/To/Tag",
      "value": 1.23,
      "quality": "Good",
      "timestamp": "2026-05-11T12:00:00.000Z"
    }
  ]
}
```

## Install For Local Development

```bash
uv sync
uv run pytest
```

## Ignition Setup

Create a WebDev project named `Fluxy` or adjust `base_url` to your chosen path.

Deploy the package-owned WebDev resource library into an Ignition project with:

```bash
uv run python -m fluxy.deploy_webdev /path/to/ignition/data/projects/flux
```

The WebDev resources are grouped under `fluxy/` so this library can be tracked independently of other WebDev resources:

- `/fluxy/tag/readBlocking`
- `/fluxy/tag/writeBlocking`
- `/fluxy/tag/copy`
- `/fluxy/tag/configure`
- `/fluxy/tag/browse`
- `/fluxy/tag/queryTags`
- `/fluxy/alarm/queryStatus`
- `/fluxy/alarm/shelve`
- `/fluxy/alarm/unshelve`
- `/fluxy/alarm/getShelvedPaths`
- `/fluxy/alarm/acknowledge`
- `/fluxy/db/...`
- `/fluxy/device/listDevices`
- `/fluxy/device/addDevice`
- `/fluxy/device/removeDevice`
- `/fluxy/device/setDeviceEnabled`
- `/fluxy/historian/browse`
- `/fluxy/historian/storeDataPoints`
- `/fluxy/historian/queryRawPoints`
- `/fluxy/historian/queryAggregatedPoints`
- `/fluxy/historian/storeAnnotations`
- `/fluxy/historian/queryAnnotations`
- `/fluxy/historian/deleteAnnotations`
- `/fluxy/historian/storeMetadata`
- `/fluxy/historian/queryMetadata`
- `/fluxy/opc/getServers`
- `/fluxy/opc/getServerState`
- `/fluxy/opc/browse`
- `/fluxy/opc/browseServer`
- `/fluxy/opc/browseSimple`
- `/fluxy/opc/readValue`
- `/fluxy/opc/readValues`
- `/fluxy/opc/writeValue`
- `/fluxy/opc/writeValues`
- `/fluxy/util/getVersion`
- `/fluxy/util/getModules`
- `/fluxy/util/getGatewayStatus`
- `/fluxy/util/getProjectName`
- `/fluxy/util/audit`
- `/fluxy/util/queryAuditLog`
- `/fluxy/report/getReportNamesAsList`
- `/fluxy/report/getReportNamesAsDataset`
- `/fluxy/report/executeReport`
- `/fluxy/user/getUserSources`
- `/fluxy/user/getRoles`
- `/fluxy/user/addRole`
- `/fluxy/user/editRole`
- `/fluxy/user/removeRole`
- `/fluxy/user/addUser`
- `/fluxy/user/getUser`
- `/fluxy/user/getUsers`
- `/fluxy/user/editUser`
- `/fluxy/user/removeUser`
- `/fluxy/user/addSchedule`
- `/fluxy/user/getSchedule`
- `/fluxy/user/getSchedules`
- `/fluxy/user/removeSchedule`
- `/fluxy/user/addHoliday`
- `/fluxy/user/getHoliday`
- `/fluxy/user/getHolidays`
- `/fluxy/user/removeHoliday`
- `/fluxy/project/requestScan`

If editing the WebDev `doPost` section manually in Designer, use the body-only script instead:

```text
ignition_webdev/designer_body/readBlocking_doPost_body.py
```

Designer adds `def doPost(request, session):` automatically. Do not paste a second function definition into that editor.

If `AUTH_TOKEN` is set in the WebDev scripts, configure the same token in Python:

```python
from fluxy import Fluxy

fx = Fluxy(base_url="https://host/system/webdev/<webdev-project>", token="same-token")
```

Security note: `writeBlocking` is powerful. The current integration tests create disposable memory tags. Before using this against real operational tags, add gateway-side auth plus an allowlist.

There is also a controlled memory-tag write/readback probe for local trials:

```bash
uv run python scripts/write_readback_generated_tags.py \
  --base-url "http://localhost:8088/system/webdev/flux"
```

## Integration Trial

The generated tag probe reads a tiny sample of full Ignition tag paths through the live WebDev bridge.

Generated-tag interface contract:

- Input files provide full Ignition tag path strings.
- Paths include providers, for example `[Tag_02]WY/AL/PADS/.../LOAD_FACTOR`.
- `fluxy` sends them to WebDev as JSON under the canonical `tagPaths` key.
- WebDev runs `system.tag.readBlocking(tag_paths, timeout_ms)` inside Ignition and returns `value`, `quality`, and `timestamp` per path.

1. Deploy the WebDev resources with `fluxy.deploy_webdev`, then call `fx.project.request_scan()`.

2. Confirm the project exposes:

```text
https://host/system/webdev/<webdev-project>/fluxy/tag/readBlocking
https://host/system/webdev/<webdev-project>/fluxy/tag/writeBlocking
https://host/system/webdev/<webdev-project>/fluxy/tag/configure
https://host/system/webdev/<webdev-project>/fluxy/tag/browse
https://host/system/webdev/<webdev-project>/fluxy/tag/queryTags
https://host/system/webdev/<webdev-project>/fluxy/db/getConnections
https://host/system/webdev/<webdev-project>/fluxy/project/requestScan
```

If `/system/webdev/<webdev-project>` returns `Resource "null" not found`, that only means the project root was reached without a resource name. Test `/fluxy/tag/readBlocking` instead.

3. Run the generated-tag probe:

```bash
uv run python scripts/read_generated_tags.py \
  --base-url "https://host/system/webdev/<webdev-project>" \
  --sample-size 3
```

Optional environment-based version:

```bash
FLUXY_BASE_URL="https://host/system/webdev/<webdev-project>" \
FLUXY_SAMPLE_SIZE=3 \
uv run python scripts/read_generated_tags.py
```

The normal pytest suite includes closed-loop live gateway integration tests:

```bash
FLUXY_BASE_URL="https://host/system/webdev/<webdev-project>" \
uv run pytest tests/test_integration_generated_tags.py
```

The write/readback test creates disposable memory tags and removes them during cleanup:

```bash
FLUXY_BASE_URL="https://host/system/webdev/<webdev-project>" \
uv run pytest tests/test_integration_generated_write_readback.py
```

The configure integration test creates memory tags, reads their configured values, writes new values, and reads them back:

```bash
FLUXY_BASE_URL="https://host/system/webdev/<webdev-project>" \
FLUXY_CONFIGURE_BASE_PATH="[Tag_02]" \
uv run pytest tests/test_integration_configure_types.py
```

The browse integration test inspects those configured memory tags:

```bash
FLUXY_BASE_URL="https://host/system/webdev/<webdev-project>" \
FLUXY_CONFIGURE_BASE_PATH="[Tag_02]" \
uv run pytest tests/test_integration_browse_configured_tags.py
```

Useful optional variables:

- `FLUXY_TOKEN`: bearer token if `AUTH_TOKEN` is configured in WebDev.
- `FLUXY_TAG_PATHS_FILE`: override the generated tag path file.
- `FLUXY_SAMPLE_SIZE`: number of tag paths to read, default `3`.
- `FLUXY_TIMEOUT_MS`: Ignition read timeout, default `45000`.
