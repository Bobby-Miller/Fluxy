from __future__ import annotations

import logging
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any

import httpx

from .alarm import AlarmClientMixin
from .db import DbClientMixin
from .device import DeviceClientMixin
from .historian import HistorianClientMixin
from .opc import OpcClientMixin
from .opcua import OpcUaClientMixin
from .project import ProjectClientMixin
from .report import ReportClientMixin
from .tag import TagClientMixin
from .user import UserClientMixin
from .util import IgnitionVersion, UtilClientMixin


LOGGER = logging.getLogger("fluxy.client")


class FluxyError(RuntimeError):
    """Raised when the Fluxy WebDev bridge rejects or cannot complete a request."""


@dataclass(frozen=True)
class ScriptRunResult:
    ok: bool
    result: Any = None
    error: str | None = None


class FluxyClient(
    TagClientMixin,
    ProjectClientMixin,
    DbClientMixin,
    DeviceClientMixin,
    HistorianClientMixin,
    UtilClientMixin,
    AlarmClientMixin,
    OpcClientMixin,
    OpcUaClientMixin,
    ReportClientMixin,
    UserClientMixin,
):
    def __init__(
        self,
        base_url: str,
        *,
        token: str | None = None,
        timeout: float = 60.0,
        read_path: str = "/fluxy/tag/readBlocking",
        write_path: str = "/fluxy/tag/writeBlocking",
        delete_path: str = "/fluxy/tag/deleteTags",
        copy_path: str = "/fluxy/tag/copy",
        move_path: str = "/fluxy/tag/move",
        rename_path: str = "/fluxy/tag/rename",
        import_path: str = "/fluxy/tag/importTags",
        export_path: str = "/fluxy/tag/exportTags",
        get_configuration_path: str = "/fluxy/tag/getConfiguration",
        configure_path: str = "/fluxy/tag/configure",
        browse_path: str = "/fluxy/tag/browse",
        query_path: str = "/fluxy/tag/queryTags",
        db_get_connections_path: str = "/fluxy/db/getConnections",
        db_get_connection_info_path: str = "/fluxy/db/getConnectionInfo",
        db_add_datasource_path: str = "/fluxy/db/addDatasource",
        db_set_datasource_connect_url_path: str = "/fluxy/db/setDatasourceConnectURL",
        db_set_datasource_enabled_path: str = "/fluxy/db/setDatasourceEnabled",
        db_set_datasource_max_connections_path: str = "/fluxy/db/setDatasourceMaxConnections",
        db_remove_datasource_path: str = "/fluxy/db/removeDatasource",
        db_begin_transaction_path: str = "/fluxy/db/beginTransaction",
        db_commit_transaction_path: str = "/fluxy/db/commitTransaction",
        db_rollback_transaction_path: str = "/fluxy/db/rollbackTransaction",
        db_close_transaction_path: str = "/fluxy/db/closeTransaction",
        db_run_query_path: str = "/fluxy/db/runQuery",
        db_run_scalar_query_path: str = "/fluxy/db/runScalarQuery",
        db_run_scalar_prep_query_path: str = "/fluxy/db/runScalarPrepQuery",
        db_run_prep_query_path: str = "/fluxy/db/runPrepQuery",
        db_run_prep_update_path: str = "/fluxy/db/runPrepUpdate",
        db_run_update_query_path: str = "/fluxy/db/runUpdateQuery",
        db_run_named_query_path: str = "/fluxy/db/runNamedQuery",
        device_list_devices_path: str = "/fluxy/device/listDevices",
        device_add_device_path: str = "/fluxy/device/addDevice",
        device_remove_device_path: str = "/fluxy/device/removeDevice",
        device_set_device_enabled_path: str = "/fluxy/device/setDeviceEnabled",
        request_scan_path: str = "/fluxy/project/requestScan",
        project_get_project_name_path: str = "/fluxy/project/getProjectName",
        project_get_project_names_path: str = "/fluxy/project/getProjectNames",
        historian_browse_path: str = "/fluxy/historian/browse",
        historian_store_data_points_path: str = "/fluxy/historian/storeDataPoints",
        historian_query_raw_points_path: str = "/fluxy/historian/queryRawPoints",
        historian_store_annotations_path: str = "/fluxy/historian/storeAnnotations",
        historian_query_annotations_path: str = "/fluxy/historian/queryAnnotations",
        historian_delete_annotations_path: str = "/fluxy/historian/deleteAnnotations",
        historian_store_metadata_path: str = "/fluxy/historian/storeMetadata",
        historian_query_metadata_path: str = "/fluxy/historian/queryMetadata",
        historian_query_aggregated_points_path: str = "/fluxy/historian/queryAggregatedPoints",
        util_get_version_path: str = "/fluxy/util/getVersion",
        util_get_modules_path: str = "/fluxy/util/getModules",
        util_get_gateway_status_path: str = "/fluxy/util/getGatewayStatus",
        util_get_project_name_path: str = "/fluxy/util/getProjectName",
        util_audit_path: str = "/fluxy/util/audit",
        util_query_audit_log_path: str = "/fluxy/util/queryAuditLog",
        alarm_query_status_path: str = "/fluxy/alarm/queryStatus",
        alarm_shelve_path: str = "/fluxy/alarm/shelve",
        alarm_unshelve_path: str = "/fluxy/alarm/unshelve",
        alarm_get_shelved_paths_path: str = "/fluxy/alarm/getShelvedPaths",
        alarm_acknowledge_path: str = "/fluxy/alarm/acknowledge",
        opc_get_servers_path: str = "/fluxy/opc/getServers",
        opc_get_server_state_path: str = "/fluxy/opc/getServerState",
        opc_browse_path: str = "/fluxy/opc/browse",
        opc_browse_server_path: str = "/fluxy/opc/browseServer",
        opc_browse_simple_path: str = "/fluxy/opc/browseSimple",
        opc_read_value_path: str = "/fluxy/opc/readValue",
        opc_read_values_path: str = "/fluxy/opc/readValues",
        opc_write_value_path: str = "/fluxy/opc/writeValue",
        opc_write_values_path: str = "/fluxy/opc/writeValues",
        opcua_add_connection_path: str = "/fluxy/opcua/addConnection",
        opcua_remove_connection_path: str = "/fluxy/opcua/removeConnection",
        report_get_names_as_list_path: str = "/fluxy/report/getReportNamesAsList",
        report_get_names_as_dataset_path: str = "/fluxy/report/getReportNamesAsDataset",
        report_execute_report_path: str = "/fluxy/report/executeReport",
        user_get_user_sources_path: str = "/fluxy/user/getUserSources",
        user_get_roles_path: str = "/fluxy/user/getRoles",
        user_add_role_path: str = "/fluxy/user/addRole",
        user_edit_role_path: str = "/fluxy/user/editRole",
        user_remove_role_path: str = "/fluxy/user/removeRole",
        user_add_user_path: str = "/fluxy/user/addUser",
        user_get_user_path: str = "/fluxy/user/getUser",
        user_get_users_path: str = "/fluxy/user/getUsers",
        user_edit_user_path: str = "/fluxy/user/editUser",
        user_remove_user_path: str = "/fluxy/user/removeUser",
        user_add_schedule_path: str = "/fluxy/user/addSchedule",
        user_get_schedule_path: str = "/fluxy/user/getSchedule",
        user_get_schedules_path: str = "/fluxy/user/getSchedules",
        user_remove_schedule_path: str = "/fluxy/user/removeSchedule",
        user_add_holiday_path: str = "/fluxy/user/addHoliday",
        user_get_holiday_path: str = "/fluxy/user/getHoliday",
        user_get_holidays_path: str = "/fluxy/user/getHolidays",
        user_remove_holiday_path: str = "/fluxy/user/removeHoliday",
        script_run_function_file_path: str = "/fluxy/scripting/runFunctionFile",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._ignition_version_cache: IgnitionVersion | None = None
        self.read_path = read_path
        self.write_path = write_path
        self.delete_path = delete_path
        self.copy_path = copy_path
        self.move_path = move_path
        self.rename_path = rename_path
        self.import_path = import_path
        self.export_path = export_path
        self.get_configuration_path = get_configuration_path
        self.configure_path = configure_path
        self.browse_path = browse_path
        self.query_path = query_path
        self.db_get_connections_path = db_get_connections_path
        self.db_get_connection_info_path = db_get_connection_info_path
        self.db_add_datasource_path = db_add_datasource_path
        self.db_set_datasource_connect_url_path = db_set_datasource_connect_url_path
        self.db_set_datasource_enabled_path = db_set_datasource_enabled_path
        self.db_set_datasource_max_connections_path = db_set_datasource_max_connections_path
        self.db_remove_datasource_path = db_remove_datasource_path
        self.db_begin_transaction_path = db_begin_transaction_path
        self.db_commit_transaction_path = db_commit_transaction_path
        self.db_rollback_transaction_path = db_rollback_transaction_path
        self.db_close_transaction_path = db_close_transaction_path
        self.db_run_query_path = db_run_query_path
        self.db_run_scalar_query_path = db_run_scalar_query_path
        self.db_run_scalar_prep_query_path = db_run_scalar_prep_query_path
        self.db_run_prep_query_path = db_run_prep_query_path
        self.db_run_prep_update_path = db_run_prep_update_path
        self.db_run_update_query_path = db_run_update_query_path
        self.db_run_named_query_path = db_run_named_query_path
        self.device_list_devices_path = device_list_devices_path
        self.device_add_device_path = device_add_device_path
        self.device_remove_device_path = device_remove_device_path
        self.device_set_device_enabled_path = device_set_device_enabled_path
        self.request_scan_path = request_scan_path
        self.project_get_project_name_path = project_get_project_name_path
        self.project_get_project_names_path = project_get_project_names_path
        self.historian_browse_path = historian_browse_path
        self.historian_store_data_points_path = historian_store_data_points_path
        self.historian_query_raw_points_path = historian_query_raw_points_path
        self.historian_store_annotations_path = historian_store_annotations_path
        self.historian_query_annotations_path = historian_query_annotations_path
        self.historian_delete_annotations_path = historian_delete_annotations_path
        self.historian_store_metadata_path = historian_store_metadata_path
        self.historian_query_metadata_path = historian_query_metadata_path
        self.historian_query_aggregated_points_path = historian_query_aggregated_points_path
        self.util_get_version_path = util_get_version_path
        self.util_get_modules_path = util_get_modules_path
        self.util_get_gateway_status_path = util_get_gateway_status_path
        self.util_get_project_name_path = util_get_project_name_path
        self.util_audit_path = util_audit_path
        self.util_query_audit_log_path = util_query_audit_log_path
        self.alarm_query_status_path = alarm_query_status_path
        self.alarm_shelve_path = alarm_shelve_path
        self.alarm_unshelve_path = alarm_unshelve_path
        self.alarm_get_shelved_paths_path = alarm_get_shelved_paths_path
        self.alarm_acknowledge_path = alarm_acknowledge_path
        self.opc_get_servers_path = opc_get_servers_path
        self.opc_get_server_state_path = opc_get_server_state_path
        self.opc_browse_path = opc_browse_path
        self.opc_browse_server_path = opc_browse_server_path
        self.opc_browse_simple_path = opc_browse_simple_path
        self.opc_read_value_path = opc_read_value_path
        self.opc_read_values_path = opc_read_values_path
        self.opc_write_value_path = opc_write_value_path
        self.opc_write_values_path = opc_write_values_path
        self.opcua_add_connection_path = opcua_add_connection_path
        self.opcua_remove_connection_path = opcua_remove_connection_path
        self.report_get_names_as_list_path = report_get_names_as_list_path
        self.report_get_names_as_dataset_path = report_get_names_as_dataset_path
        self.report_execute_report_path = report_execute_report_path
        self.user_get_user_sources_path = user_get_user_sources_path
        self.user_get_roles_path = user_get_roles_path
        self.user_add_role_path = user_add_role_path
        self.user_edit_role_path = user_edit_role_path
        self.user_remove_role_path = user_remove_role_path
        self.user_add_user_path = user_add_user_path
        self.user_get_user_path = user_get_user_path
        self.user_get_users_path = user_get_users_path
        self.user_edit_user_path = user_edit_user_path
        self.user_remove_user_path = user_remove_user_path
        self.user_add_schedule_path = user_add_schedule_path
        self.user_get_schedule_path = user_get_schedule_path
        self.user_get_schedules_path = user_get_schedules_path
        self.user_remove_schedule_path = user_remove_schedule_path
        self.user_add_holiday_path = user_add_holiday_path
        self.user_get_holiday_path = user_get_holiday_path
        self.user_get_holidays_path = user_get_holidays_path
        self.user_remove_holiday_path = user_remove_holiday_path
        self.script_run_function_file_path = script_run_function_file_path
        self._client = http_client or httpx.Client(timeout=timeout)

    def script_run_function_file(
        self,
        file_name: str,
        *args: Any,
        target_directory: str | None = None,
        **kwargs: Any,
    ) -> ScriptRunResult:
        payload = {"fileName": file_name, "args": list(args), "kwargs": kwargs}
        if target_directory is not None:
            payload["targetDirectory"] = target_directory
        response = self._post(
            self.script_run_function_file_path,
            payload,
        )
        return ScriptRunResult(
            ok=bool(response.get("ok")),
            result=response.get("result"),
            error=response.get("error"),
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = self.base_url + path
        LOGGER.debug("Fluxy request path=%s payload_keys=%s", path, sorted(payload.keys()))
        response = self._client.post(url, json=payload, headers=self._headers())
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            LOGGER.warning("Fluxy HTTP error path=%s status=%s", path, exc.response.status_code)
            raise FluxyError(
                "Fluxy bridge returned HTTP %s: %s"
                % (exc.response.status_code, exc.response.text[:500])
            ) from exc

        try:
            data = response.json()
        except JSONDecodeError as exc:
            LOGGER.warning("Fluxy non-JSON response path=%s status=%s", path, response.status_code)
            raise FluxyError(
                "Fluxy bridge returned non-JSON response from %s: HTTP %s, body=%r"
                % (url, response.status_code, response.text[:500])
            ) from exc
        if not isinstance(data, dict):
            LOGGER.warning("Fluxy non-object JSON response path=%s", path)
            raise FluxyError("Fluxy bridge response must be a JSON object")
        if data.get("ok") is False:
            LOGGER.warning("Fluxy rejected request path=%s error=%s", path, data.get("error"))
            raise FluxyError(str(data.get("error", "Fluxy bridge request failed")))
        LOGGER.debug("Fluxy response ok path=%s response_keys=%s", path, sorted(data.keys()))
        return data

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer %s" % self.token
        return headers

    def close(self) -> None:
        self._client.close()
