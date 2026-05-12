# Architecture

Current package source layout:

```text
src/fluxy/
  __init__.py
  core.py
  client/
    __init__.py
    core.py
    db/
      __init__.py
    project/
      __init__.py
    tag/
      __init__.py
  deploy_webdev/
    __init__.py
    __main__.py
    common.py
    core.py
    resource.py
    project/
      __init__.py
    db/
      __init__.py
    scripting/
      __init__.py
    tag/
      __init__.py
  deploy_scripting.py
  gateway_config.py
  named_query.py
  function_files/
    __init__.py
    hello_world.py
```

Generated `__pycache__/` directories may exist locally and are not part of the source architecture.

## Responsibilities

`core.py`

User-facing `Fluxy` facade and namespaces:

```python
fx.tag
fx.project
fx.scripting
```

`client/`

Low-level HTTP/WebDev transport and result types, split by Ignition project space:

```text
client/core.py      shared HTTP transport and FluxyClient
client/db/          database client functions such as get_connections and run_scalar_query
client/project/     project client functions such as request_scan
client/tag/         tag client functions such as read_blocking and delete_tags
```

`deploy_webdev/`

Generates and deploys Fluxy-owned WebDev resources under:

```text
com.inductiveautomation.webdev/resources/fluxy/
```

Ignition-side WebDev scripts are split by project space:

```text
deploy_webdev/core.py       shared deployment mechanics and CLI
deploy_webdev/db/          database WebDev scripts such as getConnections, addDatasource, and runScalarQuery
deploy_webdev/project/      project WebDev scripts such as requestScan
deploy_webdev/scripting/    scripting WebDev scripts such as runFunctionFile
deploy_webdev/tag/          tag WebDev scripts such as readBlocking and deleteTags
```

`deploy_scripting.py`

Deploys callable project script files under:

```text
ignition/script-python/fluxy_functions/
```

`gateway_config.py`

Deploys Gateway-scoped configuration resources that are outside the project filesystem. Current support is intentionally narrow: copy a SQLite database into the Gateway data directory and write a `core/ignition/database-connection/<name>` resource that uses the built-in `SQLite` driver and `SQLITE` translator.

`named_query.py`

Creates and deletes project named query resources under:

```text
ignition/named-query/<query_name>/
```

The current implementation supports Query-type named queries with `query.sql` and the resource attributes observed from Designer-created named queries.

`function_files/`

Bundled script fixtures/functions, currently including `hello_world.py`.

## Public API

The supported API is instance-based:

```python
from fluxy import Fluxy

fx = Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    project_location="/usr/local/bin/ignition/data/projects/flux",
    tag_provider="default",
)
```

There are no module-level `fluxy.tag`, `fluxy.project`, or `fluxy.scripting` modules in the current architecture.

## Forbidden APIs

`system.tag.exists` is explicitly forbidden and should not be implemented. Fluxy should prove tag presence through `readBlocking` quality or browse results instead of introducing a dedicated exists call. Prefer `read_blocking(...)` and monitor for `Bad_DoesNotExist`; it is more performant because it stays on the normal tag-read path.
