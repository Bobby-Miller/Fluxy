from __future__ import annotations

import argparse
import json
import shutil
import textwrap
from pathlib import Path

from . import alarm, db, device, historian, opc, opcua, project, report, scripting, tag, user, util


WEBDEV_MODULE = "com.inductiveautomation.webdev"
DEFAULT_NAMESPACE = "fluxy"


CONFIG = {
    "resource-type": "python-resource",
    "doGet": {
        "enabled": True,
        "max-retry-attempts": 3,
        "require-auth": False,
        "require-https": False,
        "required-roles": "",
        "user-source": "",
    },
    "doPost": {
        "enabled": True,
        "max-retry-attempts": 3,
        "require-auth": False,
        "require-https": False,
        "required-roles": "",
        "user-source": "",
    },
    "doPut": {
        "enabled": False,
        "max-retry-attempts": 3,
        "require-auth": False,
        "require-https": False,
        "required-roles": "",
        "user-source": "",
    },
    "doDelete": {
        "enabled": False,
        "max-retry-attempts": 3,
        "require-auth": False,
        "require-https": False,
        "required-roles": "",
        "user-source": "",
    },
    "doHead": {
        "enabled": False,
        "max-retry-attempts": 3,
        "require-auth": False,
        "require-https": False,
        "required-roles": "",
        "user-source": "",
    },
    "doOptions": {
        "enabled": False,
        "max-retry-attempts": 3,
        "require-auth": False,
        "require-https": False,
        "required-roles": "",
        "user-source": "",
    },
    "doTrace": {
        "enabled": False,
        "max-retry-attempts": 3,
        "require-auth": False,
        "require-https": False,
        "required-roles": "",
        "user-source": "",
    },
    "doPatch": {
        "enabled": False,
        "max-retry-attempts": 3,
        "require-auth": False,
        "require-https": False,
        "required-roles": "",
        "user-source": "",
    },
}

FILES = [
    "doTrace.py",
    "config.json",
    "doPut.py",
    "doHead.py",
    "doPatch.py",
    "doPost.py",
    "doOptions.py",
    "doGet.py",
    "doDelete.py",
]

STUBS = {
    "doPut.py": "def doPut(request, session):\n    pass\n",
    "doTrace.py": "def doTrace(request, session):\n    pass\n",
    "doHead.py": "def doHead(request, session):\n    pass\n",
    "doPatch.py": "def doPatch(request, session):\n    pass\n",
    "doOptions.py": "def doOptions(request, session):\n    pass\n",
    "doDelete.py": "def doDelete(request, session):\n    pass\n",
}

RESOURCES = [
    *tag.RESOURCES,
    *alarm.RESOURCES,
    *db.RESOURCES,
    *device.RESOURCES,
    *historian.RESOURCES,
    *opc.RESOURCES,
    *opcua.RESOURCES,
    *project.RESOURCES,
    *report.RESOURCES,
    *scripting.RESOURCES,
    *util.RESOURCES,
    *user.RESOURCES,
]


def deploy(
    project_path: str | Path,
    namespace: str = DEFAULT_NAMESPACE,
    clean: bool = False,
    auth_token: str | None = None,
) -> list[Path]:
    project_path = Path(project_path).resolve()
    resource_root = project_path / WEBDEV_MODULE / "resources" / namespace
    if clean and resource_root.exists():
        shutil.rmtree(resource_root)
    written = []
    for resource in RESOURCES:
        target = resource_root / resource.relative_path
        target.mkdir(parents=True, exist_ok=True)
        resource_json = {
            "scope": "G",
            "version": 1,
            "restricted": False,
            "overridable": True,
            "files": FILES,
            "attributes": {
                "lastModification": {"actor": "fluxy.deploy_webdev", "timestamp": "2026-05-11T00:00:00Z"}
            },
        }
        files = {
            "resource.json": json.dumps(resource_json, indent=2) + "\n",
            "config.json": json.dumps(CONFIG, indent=2) + "\n",
            "doGet.py": 'def doGet(request, session):\n    return {"json": {"ok": True, "resource": "%s"}}\n'
            % resource.get_resource_name,
            "doPost.py": authenticated_script(
                designer_body(resource.post_script).replace("__PROJECT_PATH__", str(project_path)),
                auth_token=auth_token,
            )
            .strip()
            + "\n",
            **STUBS,
        }
        for filename, content in files.items():
            path = target / filename
            path.write_text(content, encoding="utf-8")
            written.append(path)
    return written


def authenticated_script(script: str, auth_token: str | None = None) -> str:
    if not auth_token:
        return script
    return script.replace('AUTH_TOKEN = ""', "AUTH_TOKEN = %s" % json.dumps(auth_token), 1)


def designer_body(script: str) -> str:
    """Convert a full WebDev doPost function file into Ignition's stored body form."""
    marker = "\n\ndef doPost(request, session):\n"
    if marker not in script:
        return script
    prefix, body = script.split(marker, 1)
    return prefix.rstrip() + "\n\n" + textwrap.dedent(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy fluxy WebDev resources into an Ignition project.")
    parser.add_argument("project_path", type=Path)
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--clean", action="store_true", help="Remove the target namespace before deploying.")
    parser.add_argument("--auth-token", help="Bearer token required by deployed WebDev resources.")
    parser.add_argument("--auth-token-file", type=Path, help="File containing the bearer token to deploy.")
    return parser.parse_args()


def selected_auth_token(args: argparse.Namespace) -> str | None:
    if args.auth_token and args.auth_token_file:
        raise SystemExit("Use either --auth-token or --auth-token-file, not both.")
    if args.auth_token_file:
        return args.auth_token_file.read_text(encoding="utf-8").strip()
    return args.auth_token


def main() -> None:
    args = parse_args()
    written = deploy(
        args.project_path,
        namespace=args.namespace,
        clean=args.clean,
        auth_token=selected_auth_token(args),
    )
    print("Deployed %d files under namespace %s" % (len(written), args.namespace))
