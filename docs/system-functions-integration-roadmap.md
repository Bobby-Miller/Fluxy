# System Functions Integration Roadmap

This roadmap applies the project rule: do not expose a `system.*` function unless we can prove it with a closed-loop live test that creates disposable state, verifies behavior, and cleans up. Read-only diagnostics can be tested, but they are lower priority unless they support a disposable lifecycle test.

## Already Covered

- `system.tag`: `readBlocking`, `writeBlocking`, `deleteTags`, `copy`, `move`, `rename`, `importTags`, `exportTags`, `getConfiguration`, `configure`, `browse`, `query`.
- `system.alarm`: `queryStatus`, `shelve`, `unshelve`, `getShelvedPaths`, `acknowledge`.
- `system.db`: datasource management, connection inspection, scalar/prepared/unprepared query/update calls, transactions, named queries.
- `system.device`: `listDevices`, `addDevice`, `setDeviceEnabled`, `removeDevice` for disposable simulator devices.
- `system.historian`: `browse`, `storeDataPoints`, `queryRawPoints`, `queryAggregatedPoints`, `storeAnnotations`, `queryAnnotations`, `deleteAnnotations`, `storeMetadata`, `queryMetadata` against a configured `Core Historian` provider.
- `system.opc`: `getServers`, `getServerState`, `browse`, `browseServer`, `browseSimple`, `readValue`, `readValues`, `writeValue`, `writeValues` against disposable simulator devices.
- `system.project`: `requestScan`.
- `system.report`: `getReportNamesAsList`, `getReportNamesAsDataset`, `executeReport` against configured `test_Report` fixture.
- `system.user`: `getUserSources`, `getRoles`, `addRole`, `editRole`, `removeRole`, `addUser`, `getUser`, `getUsers`, `editUser`, `removeUser`, `addSchedule`, `getSchedule`, `getSchedules`, `removeSchedule`, `addHoliday`, `getHoliday`, `getHolidays`, `removeHoliday` against disposable users/roles/schedules/holidays.
- `system.util`: `getVersion`, `getModules`, `getGatewayStatus`, `getProjectName`, `audit`, `queryAuditLog`.
- Scripting bridge: Fluxy-owned `runFunctionFile` wrapper, not a direct Ignition `system.*` API.

## High Priority

### `system.project`

Recommended functions: none remaining; `getProjectName` and `getProjectNames` are covered.

Closed-loop test: deploy Fluxy into the known live test project, call `getProjectNames`, assert the configured project appears, call `getProjectName` from the WebDev scope, and compare to the expected project/resource context.

Reason: low-risk diagnostics that help validate deployment context and project-scan behavior.

## Medium Priority

### `system.user`

Recommended functions: none remaining from the currently proven safe lifecycle set.

Closed-loop test: require an explicit disposable user source env var, create unique role/user/schedule/holiday names, verify reads, edit role/user objects, then remove everything and assert absence.

Reason: valuable for gateway admin automation, but only safe against a test-owned user source.

### `system.roster`

Recommended functions: `createRoster`, `getRoster`, `getRosterNames`, `getRosters`, `addUsers`, `getUsers`, `removeUsers`, `deleteRoster`.

Closed-loop test: create a disposable user in a disposable user source, create a disposable roster, add/remove the user, verify membership and roster listing, then delete roster and user.

Reason: good fit if paired with `system.user`; not worth implementing before disposable user-source handling exists.

### `system.report`

Recommended functions: none remaining for basic report execution; `executeAndDistribute` is intentionally not exposed until there is a disposable delivery target.

Closed-loop test: deploy or require a disposable report resource that returns deterministic bytes/data, list reports, execute the test report with known parameters, verify output type/size/content marker, then remove the report resource and request scan.

Reason: useful, but needs a Fluxy-owned report fixture to avoid coupling tests to user reports.

## Low Priority

### `system.historian`

Recommended functions: none remaining from the proven Core Historian set.

Closed-loop test: existing tests create disposable historical paths, write known timestamped values through the historian API, query raw/aggregated values back, write/query metadata, write/query/delete annotations, and isolate all data by unique path plus narrow timestamp window.

Reason: Core Historian now has useful closed-loop API coverage without directly querying Ignition's internal QuestDB.

Implementation note: `browse`, `storeDataPoints`, `queryRawPoints`, `queryAggregatedPoints`, `storeAnnotations`, `queryAnnotations`, `deleteAnnotations`, `storeMetadata`, and `queryMetadata` are exposed after passing closed-loop tests against a configured `Core Historian` provider. `queryValues` is not exposed because it is absent from the live 8.3 `system.historian` namespace and current 8.3 docs. The WebDev bridge version-checks `system.util.getVersion()` and falls back to 8.1 `system.tag.browseHistoricalTags`, `storeTagHistory`, `queryTagHistory`, and annotation equivalents where the 8.3 `system.historian` namespace is unavailable.

## Do Not Recommend For Fluxy WebDev Exposure

### `system.tag.exists`

Never implement. Use `readBlocking` and monitor for `Bad_DoesNotExist`; this is more performant and avoids adding a dedicated gateway call.

### Async Callback APIs

Excluded functions: `system.tag.readAsync`, `system.tag.writeAsync`, `system.db.execUpdateAsync`, `system.util.invokeAsynchronous`, `system.util.sendRequestAsync`, `system.kafka.sendRecordAsync`.

Reason: callback/thread semantics do not map truthfully to a single external HTTP request/response. A real implementation would need a separate job/polling contract.

### Gateway Filesystem APIs

Excluded functions: `system.file.writeFile`, `readFileAsBytes`, `readFileAsString`, `fileExists`, `getTempFile`.

Reason: closed-loop file tests are possible, but there is no paired delete API in `system.file`, and exposing gateway filesystem access through WebDev is the wrong security boundary.

### Secrets APIs

Excluded functions: `system.secrets.encrypt`, `decrypt`, `getProviders`, `getSecrets`, `readSecretValue`.

Reason: even if encryption round-trips are testable, exposing secret providers or secret values through Fluxy is not acceptable.

### Outbound Network And Notification APIs

Excluded functions: `system.net.httpClient`, `system.net.sendEmail`, `system.net.getRemoteServers`, `system.twilio.*`, `system.util.sendRequest`, `system.net.getHostName`, `system.net.getIpAddress`.

Reason: these turn Fluxy into a network/email/SMS proxy or leak gateway network details.

### Physical Protocol Modules

Excluded namespaces: `system.bacnet`, `system.dnp`, `system.dnp3`, `system.iec61850`, `system.secsgem`, `system.serial`.

Reason: safe tests require physical or specialized external devices and cannot be generally disposable.

### Gateway/UI Session APIs

Excluded namespaces: `system.perspective`, `system.vision`, `system.print`.

Reason: WebDev gateway scope cannot reliably assert browser/session/printer behavior closed-loop.

### Admin Footguns

Excluded functions: `system.util.execute`, `system.util.setLoggingLevel`, `system.util.getGlobals`, `system.device.restart`, `system.device.setDeviceHostname`, `system.opc.setServerEnabled`.

Reason: too much blast radius for external HTTP exposure; tests can pass while still harming a live gateway.

### Pure Helper Libraries

Excluded namespaces: `system.dataset`, `system.date`, `system.math`, plus `system.util.jsonEncode` and `system.util.jsonDecode`.

Reason: deterministic transformations are better handled directly in Python unless they are needed to serialize another supported Ignition boundary.

### Optional Or Infrastructure-Heavy Namespaces

Excluded by default: `system.eam`, `system.eventstream`, `system.groups`, `system.kafka`, `system.mongodb`, `system.opcua`, `system.security`, `system.sfc`.

Reason: these either require gateway topology, preconfigured resources, running charts, or security context that Fluxy cannot create and clean up generically today.
