<!-- SPDX-FileCopyrightText: 2026 Green Pipe Partners, LLC -->
<!-- SPDX-License-Identifier: MPL-2.0 -->

# Fluxy Ignition Module

Gateway-scoped Ignition 8.1.50+ and 8.3 module artifacts that expose an allowlisted subset of Ignition scripting functions to the existing Python 3 Fluxy client.

Version `0.1.3 (b20260711)` by `Green Pipe Partners, LLC`.

## Build

The module requires Java 17. From this directory:

```bash
./gradlew -PignitionTarget=8.1 clean packageDevelopment
./gradlew -PignitionTarget=8.3 clean packageDevelopment
```

These commands build the default licensed variants. Private-use free variants are explicit:

```bash
./gradlew -PignitionTarget=8.1 -PlicenseMode=free clean test packageDevelopment
./gradlew -PignitionTarget=8.3 -PlicenseMode=free clean test packageDevelopment
```

The free artifacts are `release/Fluxy-Ignition81-Free-0.1.3.20260711-dev.unsigned.modl` and `release/Fluxy-Ignition83-Free-0.1.3.20260711-dev.unsigned.modl`, each with a SHA-256 sidecar. They declare themselves as `Fluxy Free`, return `true` from `isFreeModule()`, and do not require a trial or activated module entitlement.

All development artifacts are unsigned and for private development use. The free and licensed variants share module ID `com.greenpipepartners.fluxy`, version, routes, and configuration. They cannot be installed side by side; replace the existing artifact and restart the Gateway when changing variants.

Install only the artifact matching the Gateway's major version. The two builds intentionally share one module ID and Python contract, but they are separate binaries because Ignition changed servlet and route APIs in 8.3.

Official packaging requires `-PofficialRelease=true`, an IA-assigned nonzero `vendorId`, exact tagged source identity, and module-signing credentials. See `docs/release.md`.

## Gateway Setup

1. Install the matching `Fluxy-Ignition81` or `Fluxy-Ignition83` artifact and restart the Gateway.
2. Map the Gateway API read/write permissions to static security levels that API keys can hold.
3. Create an API key under **Platform > Security > API Keys**.
4. Grant the key read access for read, browse, and history queries. Grant write access only when configure, write, delete, or historian injection is required.
5. Use HTTPS outside a local development machine.

The 8.3 module is mounted at `/data/fluxy`. Configure the Python client with the Gateway data root:

```python
from fluxy import Fluxy

fx = Fluxy(
    "https://gateway.example/data",
    api_token="fluxy-service:<one-time-secret>",
    tag_provider="default",
    run_id="commissioning-20260711",
    script_name="build_tags.py",
)

value = fx.tag.read_blocking("[default]Demo/Value")
```

Ignition 8.1 mounts the module at `/main/data/fluxy`, so use `https://gateway.example/main/data`. Because 8.1 has no native API-key facility, configure `fluxy.apiTokenSha256` as documented in `docs/ignition-module.md`. The same Python `api_token=` argument and future-facing namespace methods work on both artifacts.

The default licensed module accepts activated licenses and unexpired Gateway trials. After trial expiry, routes return HTTP `403` with code `MODULE_TRIAL_EXPIRED`; the Python client raises `FluxyLicenseExpiredError`. Resetting the Gateway trial re-enables the same module instance. The explicit free variant bypasses this license gate but retains the same API-token authorization.

## Initial Surface

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

These are the public 8.3 names. The 8.1 dispatcher privately adapts them to `system.db.dateFormat`, `system.tag.browseHistoricalTags`, `system.tag.storeTagHistory`, and `system.tag.queryTagHistory`. Deprecated names are not exposed through the Python API.

`POST /historian/stream` is a separate native Java NDJSON route; `/historian/page` remains available through the dispatcher. The RouteGroup handler writes and flushes the servlet response directly and returns an empty renderer value. Unit tests cover this adapter contract, but installation on each supported Gateway remains the live integration gate for confirming that RouteGroup does not buffer or replace the committed response.

Arbitrary function names and script bodies are intentionally not accepted. Each new operation must be explicitly added to the module and assigned an Ignition API-key permission level.

Mutations are logged at `INFO` and written to the configured Gateway audit profile. Audit records include correlation IDs and safe targets but never process values, request bodies, or credentials. See `docs/ignition-module.md` for audit profile setup and query examples.

## License And Source

Authored module files are MPL-2.0 and copyright Green Pipe Partners, LLC, subject to the unresolved ownership gate in `PROVENANCE.md`. Every artifact embeds `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md`, `SOURCE.txt`, build identity, and a CycloneDX SBOM. The Gradle wrapper retains its upstream Apache-2.0 terms.
