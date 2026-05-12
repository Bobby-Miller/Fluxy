# Release Checklist

Fluxy is the library name, repository name, import namespace, and CLI prefix. PyPI uses the distribution name `fluxy-ign` only to avoid namespace ambiguity. The import package remains `fluxy`:

```python
from fluxy import Fluxy
```

## Install Modes

Application/project dependency:

```bash
uv add fluxy-ign
```

Tool deployment for gateway/project operations:

```bash
uv tool install fluxy-ign
```

Installed tool commands:

```bash
fluxy-deploy-webdev --help
fluxy-deploy-scripting --help
fluxy-gateway-config --help
```

## Preflight

```bash
uv run pytest -m "not integration"
uv run ruff check src tests
uv run pyright
uv build
```

## TestPyPI Dry Run

```bash
uv publish --publish-url https://test.pypi.org/legacy/
uv tool install --index-url https://test.pypi.org/simple/ --default-index https://pypi.org/simple/ fluxy-ign
fluxy-deploy-webdev --help
```

## PyPI Publish

```bash
uv publish
```

Use a scoped PyPI API token rather than username/password authentication.
