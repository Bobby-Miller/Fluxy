# Integration Tests

Integration tests require a live Ignition gateway. They are closed-loop by default: tests create disposable resources, verify behavior, and clean up.

Base environment:

```bash
cd fluxy
export FLUXY_BASE_URL="http://localhost:8088/system/webdev/flux"
```

Request project scan and verify project context through `getProjectName`/`getProjectNames`:

```bash
uv run pytest tests/test_integration_project_request_scan.py
```

Configure type tags:

```bash
FLUXY_CONFIGURE_BASE_PATH="[default]" \
uv run pytest tests/test_integration_configure_types.py
```

Browse configured tags:

```bash
FLUXY_CONFIGURE_BASE_PATH="[default]" \
uv run pytest tests/test_integration_browse_configured_tags.py
```

Configure, write, delete, and verify disposable tags are gone:

```bash
FLUXY_CONFIGURE_BASE_PATH="[default]" \
uv run pytest tests/test_integration_delete_tags.py
```

Import fixture tags, read values, export configuration, and delete the folder:

```bash
FLUXY_CONFIGURE_BASE_PATH="[default]" \
uv run pytest tests/test_integration_import_export_tags.py
```

Configure disposable tags, move one, rename one, read old/new locations, and delete the folder:

```bash
FLUXY_CONFIGURE_BASE_PATH="[default]" \
uv run pytest tests/test_integration_move_rename_tags.py
```

Configure a tag with tooltip/documentation, inspect configuration, and delete the folder:

```bash
FLUXY_CONFIGURE_BASE_PATH="[default]" \
uv run pytest tests/test_integration_get_configuration.py
```

List database connections, query `FluxyHello`, and exercise temporary SQLite datasources through `getConnections`, `getConnectionInfo`, `addDatasource`, `setDatasourceConnectURL`, `setDatasourceEnabled`, `setDatasourceMaxConnections`, `runQuery`, `runUpdateQuery`, `runScalarQuery`, `runScalarPrepQuery`, `runPrepQuery`, `runPrepUpdate`, transaction commit/rollback, mixed-type 256-row datasets, BLOB result shape, and `removeDatasource`:

```bash
uv run pytest tests/test_integration_db.py
```

Create a disposable alarm tag, write an active value, query alarm status, shelve/unshelve, optionally acknowledge event ids, and delete the tag folder:

```bash
uv run pytest tests/test_integration_alarm.py
```

Add a disposable disabled simulator device, verify it through `listDevices`, call `setDeviceEnabled`, remove it, and verify it is gone:

```bash
uv run pytest tests/test_integration_device.py
```

Add a disposable simulator device, verify OPC server state, browse device nodes, read values, write to a writable simulator node, read back, and remove the device:

```bash
uv run pytest tests/test_integration_opc.py
```

Inject timestamped points into `Core Historian`, browse the parent historian path, query raw and aggregated points back, store/query metadata, store/query/delete annotations, and verify the stored values. These tests also configure disposable memory tags and use their read values to document Core Historian datatype boundaries. The bridge uses 8.3 `system.historian.*` functions when available and contains an 8.1 `system.tag.*` historian fallback:

```bash
uv run pytest tests/test_integration_historian.py
```

If your gateway uses a different historian path, set `FLUXY_HISTORIAN_TEST_PATH_PREFIX`.

Observed Core Historian datatype boundaries in the live 8.3 gateway:

- `Boolean` stores and queries back as numeric `1.0`/`0.0`.
- `Int4`, `Int8`, and `Float8` store and query back as numeric values.
- `DateTime` tag values can be stored when represented as epoch milliseconds, and query back as a numeric millisecond value.
- `String` returns a Good store quality, but does not query back through `queryRawPoints` in this fixture.
- `Document` is rejected by `storeDataPoints`.

Read gateway diagnostics, write a unique audit event to the configured audit profile, query it back, and verify the unique target appears:

```bash
uv run pytest tests/test_integration_util.py
```

The audit test defaults to profile `Audit`; set `FLUXY_AUDIT_PROFILE` if needed.

List and execute the configured report fixture. Defaults to `test_Report`; set `FLUXY_REPORT_NAME` if needed:

```bash
uv run pytest tests/test_integration_report.py
```

Create/edit/remove a disposable role and user in the configured user source, and create/remove disposable global schedules and holidays. Defaults to `userDB`/`UserDB`; set `FLUXY_USER_SOURCE` if needed:

```bash
uv run pytest tests/test_integration_user.py
```

Add, run, delete, and verify unload of a project named query:

```bash
FLUXY_PROJECT_LOCATION="../ignition_flux_project" \
uv run pytest tests/test_integration_named_query.py
```

Read generated memory tags:

```bash
uv run pytest tests/test_integration_generated_tags.py
```

Write/readback generated memory tags:

```bash
uv run pytest tests/test_integration_generated_write_readback.py
```

Configure disposable tags, verify missing-tag quality with `readBlocking`, copy a tag, query the provider, and delete the folder:

```bash
uv run pytest tests/test_integration_tag_discovery.py
```

Run deployed `hello_world.py` through the scripting bridge:

```bash
uv run pytest tests/test_integration_scripting_run_function_file.py
```

Deploy, run, delete, and verify `hello_world.py` no longer runs:

```bash
FLUXY_PROJECT_LOCATION="../ignition_flux_project" \
uv run pytest tests/test_integration_scripting_run_function_file.py
```
