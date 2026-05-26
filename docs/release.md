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
uv run ty check src/fluxy
uv build
```

## TestPyPI Dry Run

Configure a TestPyPI trusted publisher first:

- PyPI project name: `fluxy-ign`
- Owner: `Bobby-Miller`
- Repository: `Fluxy`
- Workflow: `publish.yml`
- Environment: `testpypi`

Then run the `Publish Fluxy` GitHub Actions workflow manually with target `testpypi`.

After it publishes, install from TestPyPI:

```bash
uv tool install --index-url https://test.pypi.org/simple/ --default-index https://pypi.org/simple/ fluxy-ign
fluxy-deploy-webdev --help
```

## PyPI Publish

Configure a PyPI trusted publisher before the first release:

- PyPI project name: `fluxy-ign`
- Owner: `Bobby-Miller`
- Repository: `Fluxy`
- Workflow: `publish.yml`
- Environment: `pypi`

Publish by creating a GitHub release, or run the `Publish Fluxy` workflow manually with target `pypi`.

The workflow uses GitHub OIDC trusted publishing, so no PyPI token is stored in GitHub secrets.
