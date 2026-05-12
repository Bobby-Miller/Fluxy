from __future__ import annotations

import argparse
import json
import shutil
import textwrap
from pathlib import Path

from . import alarm, db, device, historian, opc, project, report, scripting, tag, user, util


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
    *project.RESOURCES,
    *report.RESOURCES,
    *scripting.RESOURCES,
    *util.RESOURCES,
    *user.RESOURCES,
]


def deploy(project_path: str | Path, namespace: str = DEFAULT_NAMESPACE, clean: bool = False) -> list[Path]:
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
            "doPost.py": designer_body(resource.post_script)
            .replace("__PROJECT_PATH__", str(project_path))
            .strip()
            + "\n",
            **STUBS,
        }
        for filename, content in files.items():
            path = target / filename
            path.write_text(content, encoding="utf-8")
            written.append(path)
    return written


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    written = deploy(args.project_path, namespace=args.namespace, clean=args.clean)
    print("Deployed %d files under namespace %s" % (len(written), args.namespace))
