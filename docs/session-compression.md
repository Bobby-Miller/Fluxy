# Session Compression

This is the current closeout state for the Fluxy API expansion and stress-testing work.

## Status

- Active roadmap work is complete for the selected `system.*` APIs.
- MongoDB, Kafka, and OPCUA are intentionally removed from the active roadmap.
- Direct QuestDB access is intentionally avoided; Core Historian behavior is proven through Ignition APIs.
- Latest full verification: `uv run pytest -rs` -> `131 passed`.
- Latest static checks passed: `uv run ruff check src tests scripts`, `uv run ty check src/fluxy`, and `uv run pyright`.

## Added API Coverage

- Tags: read/write/configure/browse/query/copy/move/rename/import/export/get configuration/delete.
- DB: datasource lifecycle, connection info, query/update/scalar/prep APIs, transactions, named query routing.
- Device: simulator device add/list/enable/remove.
- Historian: browse, store/query raw points, query aggregated points, store/query metadata, store/query/delete annotations.
- Project: request scan, project name diagnostics.
- Util: version/modules/gateway status/project name/audit/query audit log.
- Alarm: query status, shelve/unshelve, shelved paths, acknowledge.
- OPC: server listing/state, browse variants, read/write values.
- Report: report names as list/dataset, execute report.
- User: user sources, role lifecycle, user lifecycle, schedule lifecycle, holiday lifecycle.

## Important Boundaries

- `system.tag.exists` remains forbidden. Use `read_blocking(...)` and check quality, especially `Bad_DoesNotExist`.
- `system.historian.queryValues` is not exposed because it was absent on the live 8.3 gateway and docs route 404s.
- Historian raw data points are numeric-oriented in the live Core Historian fixture:
  - `Boolean` stores and queries as `1.0`/`0.0`.
  - `Int4`, `Int8`, and `Float8` round-trip numerically.
  - `DateTime` stores as epoch milliseconds and queries back numerically.
  - `String` can return Good store quality but does not query back through `queryRawPoints` in this fixture.
  - `Document` is rejected by `storeDataPoints`.
- DB mixed-type tests show SQLite BLOB values return byte-value lists, not base64 wrappers.
- Tag `Document` values require WebDev serialization through `toDict()`; this was fixed for `readBlocking` and recursive `getConfiguration`.

## Stress Tests Added

- Tag lifecycle stress:
  - Mixed memory types: `String`, `Boolean`, `Int4`, `Float4`, `Int8`, `Document`.
  - Configure/write/move/rename/merge/overwrite chains.
  - Collision policies: ignore, merge, overwrite.
  - Special names with spaces/dashes/underscores.
  - Copy/export/import round-trip for `Document` and `DateTime` tags.
- Tag/history boundary test:
  - Configures live memory tags, reads values, stores into Core Historian paths, and verifies accepted/rejected datatype behavior.
- DB stress:
  - 256-row mixed SQLite table.
  - Integer, real, text, nullable text, boolean-like integer, epoch millis, JSON text, and BLOB columns.
  - Prepared filters and scalar counts.

## Fixture Defaults

- Gateway URL: `http://localhost:8088/system/webdev/flux`.
- Project location: `../ignition_flux_project`.
- Tag provider: `[default]`.
- DB fixture datasource: `FluxyTestDatasource`.
- Existing hello DB: `FluxyHello`.
- Historian provider path prefix: `histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration`.
- Audit profile: `Audit`.
- OPC server: `Ignition OPC UA Server`.
- User source: `UserDB`/`userDB`.
- Report fixture: `test_Report`.

## Next Ideas

- PostgreSQL follow-up: deploy and configure a local PostgreSQL instance, add an Ignition datasource for it, then run DB integration tests against PostgreSQL-specific type behavior.
- More DB edge cases if desired: timestamps from SQL date/time functions, very large result sets, unicode text, negative/unsigned-ish BLOB byte boundaries, generated keys.
- More tag edge cases if desired: UDTs, alarm config mutation, history-enabled tag configuration, expression/reference tags.
- Harden transient gateway reload behavior only if repeated failures are reproducible; several isolated 500s were transient and passed on targeted reruns.
