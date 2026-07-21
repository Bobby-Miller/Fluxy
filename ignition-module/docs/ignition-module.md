<!-- SPDX-FileCopyrightText: 2026 Green Pipe Partners, LLC -->
<!-- SPDX-License-Identifier: MPL-2.0 -->

# Ignition Module Transport

Fluxy includes separate Gateway-scoped artifacts for Ignition 8.1.50+ and 8.3. They replace the WebDev project with native Gateway data routes while retaining one Python request and response contract.

## Architecture

```text
Python 3 Fluxy client
  -> HTTPS + API token
  -> /data/fluxy/... (8.3) or /main/data/fluxy/... (8.1)
  -> version-specific RouteGroup authorization
  -> allowlisted Jython dispatcher
  -> system.tag / system.historian / system.util
```

The dispatcher does not accept Python source or arbitrary function names. Adding a scripting function requires a module code change and an explicit read or write route assignment.

## Build

Install a Java 17 JDK, then run:

```bash
cd ignition-module
JAVA_HOME=/path/to/jdk17 ./gradlew -PignitionTarget=8.1 clean packageDevelopment
JAVA_HOME=/path/to/jdk17 ./gradlew -PignitionTarget=8.3 clean packageDevelopment
```

The development artifacts are:

- `ignition-module/release/Fluxy-Ignition81-0.1.3.20260711-dev.unsigned.modl`
- `ignition-module/release/Fluxy-Ignition83-0.1.3.20260711-dev.unsigned.modl`

Each is non-free, works during an active Ignition trial, and is explicitly marked as an unsigned development build that is not for distribution. Install only the artifact matching the Gateway major version. Both use module ID `com.greenpipepartners.fluxy`, so replace the 8.1 artifact with the 8.3 artifact as part of a Gateway upgrade.

For private use without Ignition module licensing, build the explicit free variants:

```bash
JAVA_HOME=/path/to/jdk17 ./gradlew -PignitionTarget=8.1 -PlicenseMode=free clean test packageDevelopment
JAVA_HOME=/path/to/jdk17 ./gradlew -PignitionTarget=8.3 -PlicenseMode=free clean test packageDevelopment
```

- `ignition-module/release/Fluxy-Ignition81-Free-0.1.3.20260711-dev.unsigned.modl`
- `ignition-module/release/Fluxy-Ignition83-Free-0.1.3.20260711-dev.unsigned.modl`

The free variant is identified as `Fluxy Free` in `module.xml`, sets `<freeModule>true</freeModule>`, returns `true` from the Gateway hook, and permits requests without a trial or module entitlement. It remains authenticated; "free" changes licensing, not API security.

Free and licensed artifacts share a module ID and version and therefore cannot be installed together. Replace the module artifact and restart the Gateway when switching. Do not install the 8.1 artifact on 8.3 or the 8.3 artifact on 8.1.

## Development Install

1. Enable unsigned modules only on the development Gateway by adding `-Dignition.allowunsignedmodules=true` to `data/ignition.conf`.
2. Install the unsigned development `.modl` artifact from the Gateway module page.
3. Accept the unsigned module when prompted and restart the Gateway.
4. Confirm the module is running before creating credentials.

Production artifacts must be signed. Do not enable unsigned modules on a production Gateway.

Unsigned development builds declare `Green Pipe Partners, LLC` through the module descriptor. Ignition 8.3 displays this value when unsigned modules are allowed; Ignition 8.1 displays `Unsigned` until the module is signed. For a signed production module, use a leaf code-signing certificate with `CN=Green Pipe Partners, LLC`; the certificate organization field alone does not populate the Modules page vendor column.

## Licensing

The default module participates in Ignition licensing. It permits requests when its module license is activated or while the Gateway trial is active. Ignition calls the module whenever the license state changes, including trial expiry and trial reset, so no module restart is needed for either transition.

After the trial expires, every Fluxy route stops before reading the request body or invoking Ignition scripting and returns:

```json
{
  "ok": false,
  "code": "MODULE_TRIAL_EXPIRED",
  "error": "Fluxy module trial has expired"
}
```

The HTTP status is `403 Forbidden` and the response has `Cache-Control: no-store`. A not-yet-initialized license state returns `503`. The Python client raises a specific exception for trial expiry:

```python
from fluxy import FluxyLicenseExpiredError

try:
    fx.util.get_version()
except FluxyLicenseExpiredError:
    print("Reset the Ignition trial or activate the Fluxy module license.")
```

The default distribution remains license-based. An activated production license for `com.greenpipepartners.fluxy` must be issued through Inductive Automation's third-party module licensing process. Module signing establishes artifact identity and integrity but does not activate a commercial license. Activated versions do not perform a maintenance-expiration check; version entitlement restrictions will be added only after IA assigns and documents the applicable licensing parameters.

The `-PlicenseMode=free` build is an unsigned private-use convenience variant. It is not the official supported commercial artifact and should not be represented as signed, IA-approved, or licensed.

## Authorization

### Ignition 8.3

Ignition API keys are subject to the Gateway API Access, Read, and Write permission settings under **Platform > Security > General Settings**. Configure those permissions with a static security level that the service API key is allowed to hold. Do not rely on user-source roles: Ignition intentionally ignores role levels granted directly by API-key configuration.

For a local-only trial, all three Gateway API permissions can require `Authenticated`, and the API key can hold `Authenticated`. A production deployment should use dedicated static levels and separate read-only and write-enabled keys.

Create an API key under **Platform > Security > API Keys**. Pass the complete credential displayed by Ignition, including its key name:

```python
from fluxy import Fluxy

fx = Fluxy(
    "https://gateway.example/data",
    api_token="fluxy-service:<one-time-secret>",
    tag_provider="default",
    run_id="commissioning-20260711",
    script_name="build_tags.py",
)
```

Use HTTPS. An API key is a bearer credential even though it uses the `X-Ignition-API-Token` header.

### Ignition 8.1

Ignition 8.1 does not provide native Gateway API keys. The 8.1 artifact verifies SHA-256 token hashes configured as JVM properties and accepts the same `X-Ignition-API-Token` header used by `api_token=`.

Generate a random token, calculate its hash without a trailing newline, and add the hash to `data/ignition.conf` using the next available `wrapper.java.additional.N` index:

```bash
printf '%s' 'replace-with-a-random-token' | sha256sum
```

```properties
wrapper.java.additional.N=-Dfluxy.apiTokenSha256=<64-character-write-token-sha256>
wrapper.java.additional.M=-Dfluxy.readApiTokenSha256=<optional-read-only-token-sha256>
```

Restart the Gateway after changing the properties. The write token can call all routes; the optional read token can call only read routes. Store only hashes in Gateway configuration, use at least 256 random bits for each token, and put a TLS reverse proxy in front of the 8.1 Gateway for rate and request-size limits.

```python
fx = Fluxy(
    "https://gateway.example/main/data",
    api_token="replace-with-a-random-token",
)
```

## Traceability And Auditing

Fluxy assigns a UUID request ID to every Gateway call. A `Fluxy` instance also has one stable run ID, generated automatically unless `run_id` is supplied. Set `script_name` to identify the calling automation.

The client sends:

- `X-Fluxy-Request-Id`: unique per operation.
- `X-Fluxy-Run-Id`: stable across one script or batch run.
- `X-Fluxy-Script`: optional caller-provided script name.

The module returns the accepted request and run IDs as response headers. The latest request ID is available as:

```python
print(fx.client.last_request_id)
print(fx.client.last_run_id)
```

Successful mutations are logged at `INFO` under `Fluxy.Module`. Reads are logged at `DEBUG`, and failed calls are logged at `WARN` or `ERROR`. Each entry includes the API-key actor, operation, request ID, run ID, script, status, duration, target count, and safe target paths.

Mutation records are also sent to Ignition's configured Gateway audit profile. Configure one under **Platform > Security > Audit Profiles**, then select it as the Gateway audit profile under **Platform > Security > General Settings**. A local profile named `Fluxy Audit` works without an external database.

Audited module operations currently include:

- `tag/configure`
- `tag/writeBlocking`
- `tag/deleteTags`
- `historian/storeDataPoints`

Audit records contain actor, host, operation, targets, request ID, run ID, script, HTTP status, duration, target count, contract version, timestamp, and result quality. Tag values, historian values, API keys, and complete request bodies are never logged or audited.

Query the resulting records through Fluxy:

```python
rows = fx.util.query_audit_log(
    "Fluxy Audit",
    action_filter="Fluxy.tag/writeBlocking",
    target_filter="[default]Area/Setpoint",
)

for row in rows:
    print(row)
```

If no Gateway audit profile is configured, mutations still execute and remain in Gateway logs. The module emits a one-time warning that durable auditing is disabled.

## Version Adapters

The Python API and route names remain future-facing on both versions. The 8.1 artifact performs these private adaptations:

| Public operation | Ignition 8.3 | Ignition 8.1 |
| --- | --- | --- |
| Tag timestamp formatting | `system.date.format` | `system.db.dateFormat` |
| `historian.browse` | `system.historian.browse` | `system.tag.browseHistoricalTags` |
| `historian.store_data_points` | `system.historian.storeDataPoints` | `system.tag.storeTagHistory` |
| `historian.query_raw_points` | `system.historian.queryRawPoints` | `system.tag.queryTagHistory` |

The native module does not currently expose `system.db` query/cache or Vision binding routes. When those routes are added, modern Python names such as `exec_query`, `exec_scalar`, `exec_update`, and `clear_cache` should remain public while each artifact selects its version-specific Ignition function internally.

## Historian Trial

History calls require an enabled historian provider. For the built-in 8.3 provider:

1. Open **Connections > Historians**.
2. Create a provider named `Core Historian`.
3. Configure memory tags with `historyEnabled: true` and `historyProvider: "Core Historian"`.

Do not assume tag history is stored under `sys:gateway`. Directly injected points may use that system node, while tag-generated samples use the Gateway's normalized system name. Use `fx.historian.browse("histprov:Core Historian:/")` to discover the canonical path.

## Live Verification

The opt-in test configures a history-enabled memory tag, writes and reads values, browses tags and historian paths, queries history, and deletes the tag:

```bash
FLUXY_MODULE_INTEGRATION=1 \
FLUXY_BASE_URL=http://localhost:8088/data \
FLUXY_API_TOKEN='fluxy-service:<one-time-secret>' \
uv run pytest ignition-module/tests/test_integration_module.py
```

## Current Surface

- `system.util.getVersion`
- `system.util.queryAuditLog`
- `system.tag.configure`
- `system.tag.readBlocking`
- `system.tag.writeBlocking`
- `system.tag.browse`
- `system.tag.getConfiguration`
- `system.tag.deleteTags`
- `system.historian.browse`
- `system.historian.storeDataPoints`
- `system.historian.queryRawPoints`

The WebDev transport remains available for existing deployments. The native artifacts target 8.1.50 and 8.3.4 respectively because the major versions have incompatible servlet and route-authorization APIs.

Current module release: `0.1.3 (b20260711)`, vendor `Green Pipe Partners, LLC`.

The module source is MPL-2.0. See `../LICENSE`, `../NOTICE`, `../PROVENANCE.md`, and `release.md` for source, ownership, and official-release requirements.
