from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from importlib import resources
from pathlib import Path


SCRIPT_ROOT = Path("ignition") / "script-python" / "fluxy_functions"
SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.py)?$")
SAFE_DIRECTORY_PART = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def function_stem(file_name: str) -> str:
    if not SAFE_NAME.match(file_name):
        raise ValueError("Function file names must be Python identifiers with optional .py suffix")
    return file_name[:-3] if file_name.endswith(".py") else file_name


def target_directory_path(target_directory: str | Path | None = None) -> Path:
    if target_directory is None or str(target_directory).strip() in {"", "."}:
        return Path()
    target = Path(target_directory)
    if target.is_absolute() or ".." in target.parts:
        raise ValueError("target_directory must be a relative path inside fluxy_functions")
    if any(not SAFE_DIRECTORY_PART.match(part) for part in target.parts):
        raise ValueError("target_directory parts must be Python identifiers")
    return target


def function_resource_path(
    project_path: str | Path, file_name: str, target_directory: str | Path | None = None
) -> Path:
    project_path = Path(project_path)
    stem = function_stem(file_name)
    return project_path / SCRIPT_ROOT / target_directory_path(target_directory) / stem


def deploy_function_file(
    project_path: str | Path,
    file_name: str,
    source: str,
    target_directory: str | Path | None = None,
) -> Path:
    target = function_resource_path(project_path, file_name, target_directory)
    target.mkdir(parents=True, exist_ok=True)
    code_path = target / "code.py"
    code_path.write_text(source.rstrip() + "\n", encoding="utf-8")
    signature = hashlib.sha256(source.encode("utf-8")).hexdigest()
    (target / "resource.json").write_text(
        """{
  "scope": "A",
  "version": 1,
  "restricted": false,
  "overridable": true,
  "files": [
    "code.py"
  ],
  "attributes": {
    "lastModificationSignature": "%s",
    "hintScope": 2,
    "lastModification": {
      "actor": "fluxy.deploy_scripting",
      "timestamp": "2026-05-11T00:00:00Z"
    }
  }
}
"""
        % signature,
        encoding="utf-8",
    )
    return code_path


def deploy_builtin_function_file(
    project_path: str | Path,
    file_name: str,
    target_directory: str | Path | None = None,
) -> Path:
    stem = function_stem(file_name)
    source = (
        resources.files("fluxy.function_files").joinpath(stem + ".py").read_text(encoding="utf-8")
    )
    return deploy_function_file(project_path, file_name, source, target_directory=target_directory)


def delete_function_file(
    project_path: str | Path,
    file_name: str,
    target_directory: str | Path | None = None,
) -> Path:
    target = function_resource_path(project_path, file_name, target_directory)
    if target.exists():
        shutil.rmtree(target)
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy fluxy scripting function files.")
    parser.add_argument("project_path", type=Path)
    parser.add_argument("file_name")
    parser.add_argument("--target-directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = deploy_builtin_function_file(
        args.project_path, args.file_name, target_directory=args.target_directory
    )
    print("Deployed %s" % path)


if __name__ == "__main__":
    main()
