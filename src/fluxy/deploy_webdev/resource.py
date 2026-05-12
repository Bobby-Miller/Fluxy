from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebDevResource:
    relative_path: str
    get_resource_name: str
    post_script: str
