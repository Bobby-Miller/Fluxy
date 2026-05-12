from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Protocol

from fluxy.client.db import QueryResult
from fluxy.client.db.DB import query_result_from_response


class ReportTransport(Protocol):
    report_get_names_as_list_path: str
    report_get_names_as_dataset_path: str
    report_execute_report_path: str

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ReportExecutionResult:
    content: bytes
    file_type: str


class ReportClientMixin:
    def report_get_names_as_list(self: ReportTransport, project: str) -> list[str]:
        response = self._post(self.report_get_names_as_list_path, {"project": project})
        reports = response.get("reports")
        if not isinstance(reports, list):
            from fluxy.client import FluxyError

            raise FluxyError("getReportNamesAsList response missing `reports` list")
        return [str(report) for report in reports]

    def report_get_names_as_dataset(
        self: ReportTransport,
        project: str,
        include_report_name: bool = True,
    ) -> QueryResult:
        return query_result_from_response(
            self._post(
                self.report_get_names_as_dataset_path,
                {"project": project, "includeReportName": include_report_name},
            )
        )

    def report_execute_report(
        self: ReportTransport,
        path: str,
        project: str,
        parameters: dict[str, Any] | None = None,
        file_type: str = "pdf",
    ) -> ReportExecutionResult:
        response = self._post(
            self.report_execute_report_path,
            {
                "path": path,
                "project": project,
                "parameters": parameters or {},
                "fileType": file_type,
            },
        )
        encoded = response.get("contentBase64")
        if not isinstance(encoded, str):
            from fluxy.client import FluxyError

            raise FluxyError("executeReport response missing `contentBase64` string")
        return ReportExecutionResult(
            content=base64.b64decode(encoded),
            file_type=str(response.get("fileType") or file_type),
        )
