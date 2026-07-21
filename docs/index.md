# Fluxy Documentation

Fluxy is a Python client with Ignition WebDev and native Ignition 8.1.50+/8.3 module transports for selected Ignition APIs.

Canonical Python style is snake_case:

- `fx.tag.read_blocking(...)`
- `fx.tag.write_blocking(...)`
- `fx.tag.configure(...)`
- `fx.tag.browse(...)`
- `fx.project.request_scan()`

Ignition-style aliases exist only as porting shims:

- `fx.tag.readBlocking(...)`
- `fx.tag.writeBlocking(...)`
- `fx.project.requestScan()`

## Docs

- `webdev-deployment.md`: deploy and reload the Ignition WebDev resources.
- [Gateway module documentation](https://github.com/GreenPipePartners/Fluxy/tree/main/ignition-module/docs/ignition-module.md): build, install, secure, license, and test the version-specific Gateway modules.
- `product-offering.md`: website-ready positioning, required pages, and launch blockers for Fluxy Official.
- `auth.md`: protect Fluxy WebDev access with a bearer token and verify clients.
- `api.md`: public Python API.
- `user-guide.md`: end-to-end user workflow.
- `architecture.md`: current package layout and responsibilities.
- `integration-tests.md`: live gateway test commands.
- `gateway-config.md`: Gateway-scoped SQLite database connection deployment.
- `system-functions-integration-roadmap.md`: recommended `system.*` integrations and required closed-loop tests.
- `session-compression.md`: closeout summary of current API coverage, boundaries, fixtures, and next ideas.
- `release.md`: PyPI and `uv tool` release checklist.
