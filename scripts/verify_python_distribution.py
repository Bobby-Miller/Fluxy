# SPDX-FileCopyrightText: 2026 Green Pipe Partners, LLC
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path


FORBIDDEN_PARTS = ("ignition-module", "script.py")
FORBIDDEN_SUFFIXES = (".jar", ".modl")
FORBIDDEN_NAMES = {
    "module.xml",
    "SOURCE.txt",
    "THIRD_PARTY_NOTICES.md",
    "WEBDEV_MIT_NOTICE",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the MIT-only Python distribution boundary.")
    parser.add_argument("dist", nargs="?", default="dist", type=Path)
    args = parser.parse_args()

    wheel = exactly_one(args.dist.glob("*.whl"), "wheel")
    source = exactly_one(args.dist.glob("*.tar.gz"), "source distribution")
    verify_wheel(wheel)
    verify_source(source)
    print("Python distributions declare MIT and contain no Gateway module paths or artifacts.")
    return 0


def exactly_one(paths, description: str) -> Path:
    matches = list(paths)
    if len(matches) != 1:
        raise RuntimeError("Expected one %s, found %d" % (description, len(matches)))
    return matches[0]


def reject_forbidden(names: list[str]) -> None:
    for name in names:
        parts = Path(name).parts
        if any(part in FORBIDDEN_PARTS for part in parts):
            raise RuntimeError("Forbidden module path in Python distribution: %s" % name)
        if name.endswith(FORBIDDEN_SUFFIXES):
            raise RuntimeError("Forbidden module artifact in Python distribution: %s" % name)
        if Path(name).name in FORBIDDEN_NAMES or name.endswith(".cdx.json"):
            raise RuntimeError("Forbidden module compliance file in Python distribution: %s" % name)


def verify_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        reject_forbidden(names)
        metadata_name = exactly_one(
            (Path(name) for name in names if name.endswith(".dist-info/METADATA")),
            "wheel metadata file",
        )
        metadata = archive.read(str(metadata_name)).decode("utf-8")
        if "License-Expression: MIT" not in metadata:
            raise RuntimeError("Wheel metadata does not declare MIT")
        for name in names:
            if name.endswith(".py") and b"SPDX-License-Identifier: MPL-2.0" in archive.read(name):
                raise RuntimeError("MPL-covered Python source found in wheel: %s" % name)


def verify_source(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
        reject_forbidden(names)
        package_info = exactly_one(
            (Path(name) for name in names if Path(name).name == "PKG-INFO"),
            "source distribution metadata file",
        )
        metadata_file = archive.extractfile(str(package_info))
        if metadata_file is None or b"License-Expression: MIT" not in metadata_file.read():
            raise RuntimeError("Source distribution metadata does not declare MIT")
        for name in names:
            if not name.endswith(".py"):
                continue
            source_file = archive.extractfile(name)
            if source_file is not None and b"SPDX-License-Identifier: MPL-2.0" in source_file.read():
                raise RuntimeError("MPL-covered Python source found in source distribution: %s" % name)


if __name__ == "__main__":
    raise SystemExit(main())
