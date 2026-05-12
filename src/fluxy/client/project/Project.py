from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RequestScanResult:
    ok: bool
    message: str | None = None


class ProjectTransport(Protocol):
    request_scan_path: str
    project_get_project_name_path: str
    project_get_project_names_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class ProjectClientMixin:
    def request_scan(self: ProjectTransport) -> RequestScanResult:
        response = self._post(self.request_scan_path, {})
        return RequestScanResult(ok=bool(response.get("ok")), message=response.get("message"))

    def project_get_project_name(self: ProjectTransport) -> str:
        response = self._post(self.project_get_project_name_path, {})
        return str(response.get("projectName") or "")

    def project_get_project_names(self: ProjectTransport) -> list[str]:
        response = self._post(self.project_get_project_names_path, {})
        project_names = response.get("projectNames")
        if not isinstance(project_names, list):
            from fluxy.client import FluxyError

            raise FluxyError("getProjectNames response missing `projectNames` list")
        return [str(project_name) for project_name in project_names]
