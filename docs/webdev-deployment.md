# WebDev Deployment

Fluxy owns a deployable library of Ignition WebDev resources in `fluxy.deploy_webdev`.

Deploy into an Ignition project folder:

```bash
cd fluxy
uv run python -m fluxy.deploy_webdev /usr/local/bin/ignition/data/projects/flux
```

The deployer writes resources under a dedicated `fluxy/` WebDev namespace:

```text
com.inductiveautomation.webdev/resources/fluxy/tag/readBlocking
com.inductiveautomation.webdev/resources/fluxy/tag/writeBlocking
com.inductiveautomation.webdev/resources/fluxy/tag/deleteTags
com.inductiveautomation.webdev/resources/fluxy/tag/move
com.inductiveautomation.webdev/resources/fluxy/tag/rename
com.inductiveautomation.webdev/resources/fluxy/tag/importTags
com.inductiveautomation.webdev/resources/fluxy/tag/exportTags
com.inductiveautomation.webdev/resources/fluxy/tag/getConfiguration
com.inductiveautomation.webdev/resources/fluxy/tag/configure
com.inductiveautomation.webdev/resources/fluxy/tag/browse
com.inductiveautomation.webdev/resources/fluxy/db/getConnections
com.inductiveautomation.webdev/resources/fluxy/db/addDatasource
com.inductiveautomation.webdev/resources/fluxy/db/removeDatasource
com.inductiveautomation.webdev/resources/fluxy/db/runScalarQuery
com.inductiveautomation.webdev/resources/fluxy/db/runNamedQuery
com.inductiveautomation.webdev/resources/fluxy/project/requestScan
com.inductiveautomation.webdev/resources/fluxy/scripting/runFunctionFile
```

After deploying, request an Ignition project scan:

```python
from fluxy import Fluxy

fx = Fluxy(base_url="http://localhost:8088/system/webdev/flux")
fx.project.request_scan()
```

This replaces the old timer workflow. Future WebDev updates should follow this loop:

```text
edit fluxy.deploy_webdev -> deploy -> fx.project.request_scan() -> run integration tests
```

Expected live routes:

```text
/system/webdev/flux/fluxy/tag/readBlocking
/system/webdev/flux/fluxy/tag/writeBlocking
/system/webdev/flux/fluxy/tag/deleteTags
/system/webdev/flux/fluxy/tag/move
/system/webdev/flux/fluxy/tag/rename
/system/webdev/flux/fluxy/tag/importTags
/system/webdev/flux/fluxy/tag/exportTags
/system/webdev/flux/fluxy/tag/getConfiguration
/system/webdev/flux/fluxy/tag/configure
/system/webdev/flux/fluxy/tag/browse
/system/webdev/flux/fluxy/db/getConnections
/system/webdev/flux/fluxy/db/addDatasource
/system/webdev/flux/fluxy/db/removeDatasource
/system/webdev/flux/fluxy/db/runScalarQuery
/system/webdev/flux/fluxy/db/runNamedQuery
/system/webdev/flux/fluxy/project/requestScan
/system/webdev/flux/fluxy/scripting/runFunctionFile
```

Deploy built-in scripting function files:

```bash
uv run python -m fluxy.deploy_scripting /usr/local/bin/ignition/data/projects/flux hello_world.py
```

Optionally deploy under a target directory below `fluxy_functions/`:

```bash
uv run python -m fluxy.deploy_scripting /usr/local/bin/ignition/data/projects/flux hello_world.py --target-directory scratch
```

Function files are written under:

```text
ignition/script-python/fluxy_functions/[target_directory/]<function_name>/code.py
```
