# Fluxy Auth

Fluxy uses a simple bearer token to protect its Ignition WebDev bridge.

This is not an Ignition Gateway login, identity provider login, or user-source password. Ignition still controls which project resources exist and what the WebDev scripts are allowed to do inside the Gateway. The Fluxy token only answers one question: can this outside Python client call the deployed Fluxy WebDev endpoints?

## Auth Boundary

Fluxy access has two sides:

- Ignition side: deployed WebDev resources contain an optional `AUTH_TOKEN` value.
- Python side: `Fluxy(..., token="...")`, `FLUXY_TOKEN`, or `--token-file` sends `Authorization: Bearer <token>`.

If the deployed `AUTH_TOKEN` is blank, Fluxy WebDev auth is disabled. This can be acceptable for local disposable development, but production-like gateways should deploy with a token.

## Create A Token

Create a token file outside committed source control:

```bash
mkdir -p .secrets
python - <<'PY'
import secrets
from pathlib import Path

Path(".secrets/fluxy-token").write_text(secrets.token_urlsafe(32) + "\n", encoding="utf-8")
PY
```

Do not commit this file.

## Deploy Protected WebDev Resources

Deploy Fluxy-owned WebDev endpoints into the Ignition project filesystem with the token embedded in each endpoint script:

```bash
uv run fluxy-deploy-webdev \
  /usr/local/bin/ignition/data/projects/flux \
  --auth-token-file .secrets/fluxy-token
```

From the package module directly:

```bash
uv run python -m fluxy.deploy_webdev \
  /usr/local/bin/ignition/data/projects/flux \
  --auth-token-file .secrets/fluxy-token
```

Then request an Ignition project scan so the Gateway reloads the WebDev resources:

```python
from fluxy import Fluxy

fx = Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    token="paste-token-here",
)
fx.project.request_scan()
```

During token rotation, the currently loaded WebDev scripts still enforce the old token until the scan completes. If `request_scan()` returns `401` after changing the deployed token, retry the scan with the old token or trigger the project scan manually from the Gateway.

If you do not want to paste the token, load it from the same file:

```python
from pathlib import Path

from fluxy import Fluxy

token = Path(".secrets/fluxy-token").read_text(encoding="utf-8").strip()

fx = Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    token=token,
)
fx.project.request_scan()
```

## Configure Clients

Python code can pass the token directly:

```python
from fluxy import Fluxy

fx = Fluxy(
    base_url="http://localhost:8088/system/webdev/flux",
    token="shared-secret-token",
)
print(fx.util.get_version())
```

Shell workflows can use `FLUXY_TOKEN`:

```bash
export FLUXY_BASE_URL="http://localhost:8088/system/webdev/flux"
export FLUXY_TOKEN="$(tr -d '\n' < .secrets/fluxy-token)"
```

MCP can read the token file directly:

```bash
uv run --extra mcp fluxy-mcp \
  --base-url http://localhost:8088/system/webdev/flux \
  --token-file .secrets/fluxy-token
```

## Verify Access

Use the dev check when available:

```bash
uv run python -m fluxy.check_ignition_dev \
  --fluxy-base-url "$FLUXY_BASE_URL" \
  --token "$FLUXY_TOKEN"
```

Expected result includes:

```text
[OK] Fluxy WebDev: Fluxy WebDev is reachable.
```

You can also verify from Python:

```python
import os

from fluxy import Fluxy

fx = Fluxy(
    base_url=os.environ["FLUXY_BASE_URL"],
    token=os.environ.get("FLUXY_TOKEN"),
)
print(fx.util.get_version())
```

## Troubleshooting

- `401` or `403`: the client token does not match the token deployed into WebDev, or the client did not send a token.
- `404`: the Fluxy WebDev resources are not deployed at that base URL, or Ignition has not scanned the project after deployment.
- Non-JSON HTML response: the Gateway may need manual attention, such as trial/license handling or a login page redirect.
- Token change has no effect: redeploy WebDev with the new token and request another project scan. Use the old token for that scan if the loaded endpoint has not reloaded yet.
- Local tests fail only on a protected bridge: export `FLUXY_TOKEN` before running tests.

If you intentionally want unauthenticated local access, deploy without `--auth-token` or `--auth-token-file`. That leaves `AUTH_TOKEN` blank in the WebDev scripts, and Fluxy accepts requests without an `Authorization` header.
