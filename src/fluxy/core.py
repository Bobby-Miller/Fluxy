from __future__ import annotations

from pathlib import Path
from typing import Any, overload

import httpx

from .client import (
    BrowseResult,
    ConfigureResult,
    DatabaseConnection,
    DeleteResult,
    DeviceConnection,
    ExportTagsResult,
    FluxyClient,
    FluxyError,
    HistorianAnnotation,
    HistorianBrowseResult,
    HistorianMetadata,
    ImportResult,
    IgnitionVersion,
    MoveResult,
    OpcValue,
    QualifiedValue,
    QueryResult,
    RenameResult,
    ReportExecutionResult,
    RequestScanResult,
    ScriptRunResult,
    UserResponse,
    WriteResult,
)
from .deploy_scripting import delete_function_file, deploy_builtin_function_file, deploy_function_file
from .deploy_webdev import deploy as deploy_webdev_resources
from .named_query import NamedQueryRunner, add_named_query, delete_named_query


class Fluxy:
    def __init__(
        self,
        base_url: str,
        *,
        project_location: str | Path | None = None,
        tag_provider: str | None = None,
        token: str | None = None,
        timeout: float = 60.0,
        http_client: httpx.Client | None = None,
        named_query_runner: NamedQueryRunner | None = None,
    ) -> None:
        self.client = FluxyClient(
            base_url=base_url,
            token=token,
            timeout=timeout,
            http_client=http_client,
        )
        self.project_location = Path(project_location).resolve() if project_location is not None else None
        self.tag_provider = tag_provider
        self.named_query_runner = named_query_runner
        self.tag = TagNamespace(self)
        self.db = DbNamespace(self)
        self.device = DeviceNamespace(self)
        self.historian = HistorianNamespace(self)
        self.util = UtilNamespace(self)
        self.opc = OpcNamespace(self)
        self.opcua = OpcUaNamespace(self)
        self.named_query = NamedQueryNamespace(self)
        self.project = ProjectNamespace(self)
        self.report = ReportNamespace(self)
        self.user = UserNamespace(self)
        self.scripting = ScriptingNamespace(self)
        self.alarm = AlarmNamespace(self)

    def require_project_location(self) -> Path:
        if self.project_location is None:
            raise FluxyError("project_location is required for this operation")
        return self.project_location

    def default_tag_base_path(self) -> str:
        if not self.tag_provider:
            raise FluxyError("tag_provider is required when base_path is omitted")
        if self.tag_provider.startswith("[") and self.tag_provider.endswith("]"):
            return self.tag_provider
        return "[%s]" % self.tag_provider

    def deploy_webdev(
        self,
        *,
        namespace: str = "fluxy",
        clean: bool = False,
        auth_token: str | None = None,
    ) -> list[Path]:
        selected_auth_token = self.client.token if auth_token is None else auth_token
        return deploy_webdev_resources(
            self.require_project_location(),
            namespace=namespace,
            clean=clean,
            auth_token=selected_auth_token,
        )

    def close(self) -> None:
        self.client.close()


class TagNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    @overload
    def read_blocking(
        self, tag_paths: str, timeout: int | None = None, timeout_ms: int | None = None
    ) -> QualifiedValue: ...

    @overload
    def read_blocking(
        self, tag_paths: list[str], timeout: int | None = None, timeout_ms: int | None = None
    ) -> list[QualifiedValue]: ...

    def read_blocking(
        self, tag_paths: str | list[str], timeout: int | None = None, timeout_ms: int | None = None
    ) -> QualifiedValue | list[QualifiedValue]:
        selected_timeout = timeout if timeout is not None else timeout_ms
        return self._fluxy.client.read_blocking(tag_paths, timeout_ms=selected_timeout)

    @overload
    def write_blocking(
        self, tag_paths: str, values: Any, timeout: int | None = None, timeout_ms: int | None = None
    ) -> WriteResult: ...

    @overload
    def write_blocking(
        self,
        tag_paths: list[str],
        values: list[Any],
        timeout: int | None = None,
        timeout_ms: int | None = None,
    ) -> list[WriteResult]: ...

    def write_blocking(
        self,
        tag_paths: str | list[str],
        values: Any | list[Any],
        timeout: int | None = None,
        timeout_ms: int | None = None,
    ) -> WriteResult | list[WriteResult]:
        selected_timeout = timeout if timeout is not None else timeout_ms
        return self._fluxy.client.write_blocking(tag_paths, values, timeout_ms=selected_timeout)

    @overload
    def delete_tags(self, tag_paths: str) -> DeleteResult: ...

    @overload
    def delete_tags(self, tag_paths: list[str]) -> list[DeleteResult]: ...

    def delete_tags(self, tag_paths: str | list[str]) -> DeleteResult | list[DeleteResult]:
        return self._fluxy.client.delete_tags(tag_paths)

    def copy(
        self, tag_paths: str | list[str], destination_path: str, collision_policy: str = "o"
    ) -> Any:
        return self._fluxy.client.copy(tag_paths, destination_path, collision_policy=collision_policy)

    def move(self, source_path: str, destination_path: str) -> MoveResult:
        return self._fluxy.client.move(source_path, destination_path)

    def rename(self, tag_path: str, new_name: str) -> RenameResult:
        return self._fluxy.client.rename(tag_path, new_name)

    def import_tags(
        self,
        tags: Any,
        base_path: str | None = None,
        collision_policy: str = "o",
    ) -> list[ImportResult]:
        return self._fluxy.client.import_tags(
            tags,
            base_path or self._fluxy.default_tag_base_path(),
            collision_policy=collision_policy,
        )

    def export_tags(self, tag_paths: str | list[str], recursive: bool = True) -> ExportTagsResult:
        return self._fluxy.client.export_tags(tag_paths, recursive=recursive)

    def get_configuration(self, path: str, recursive: bool = False) -> list[dict[str, Any]]:
        return self._fluxy.client.get_configuration(path, recursive=recursive)

    def configure(
        self,
        tags: list[dict[str, Any]],
        base_path: str | None = None,
        collision_policy: str = "o",
    ) -> list[ConfigureResult]:
        return self._fluxy.client.configure(
            base_path or self._fluxy.default_tag_base_path(),
            tags,
            collision_policy=collision_policy,
        )

    def browse(
        self, path: str | None = None, tag_filter: dict[str, Any] | None = None
    ) -> list[BrowseResult]:
        return self._fluxy.client.browse(path or self._fluxy.default_tag_base_path(), tag_filter=tag_filter)

    def query(
        self,
        provider: str | None = None,
        query: dict[str, Any] | None = None,
        limit: int | None = None,
        continuation: str | None = None,
    ) -> Any:
        selected_provider = provider or self._fluxy.tag_provider or "default"
        return self._fluxy.client.query(selected_provider, query=query, limit=limit, continuation=continuation)

    # Ignition-style aliases for porting scripts.
    readBlocking = read_blocking
    writeBlocking = write_blocking
    deleteTags = delete_tags
    copy = copy
    importTags = import_tags
    exportTags = export_tags
    getConfiguration = get_configuration


class ProjectNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def request_scan(self) -> RequestScanResult:
        return self._fluxy.client.request_scan()

    def get_project_name(self) -> str:
        return self._fluxy.client.project_get_project_name()

    def get_project_names(self) -> list[str]:
        return self._fluxy.client.project_get_project_names()

    # Ignition-style alias for porting scripts.
    requestScan = request_scan
    getProjectName = get_project_name
    getProjectNames = get_project_names


class DeviceNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def list_devices(self) -> list[DeviceConnection]:
        return self._fluxy.client.device_list_devices()

    def add_device(
        self,
        device_type: str,
        device_name: str,
        device_props: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> bool:
        return self._fluxy.client.device_add_device(
            device_type,
            device_name,
            device_props=device_props,
            description=description,
        )

    def remove_device(self, device_name: str) -> bool:
        return self._fluxy.client.device_remove_device(device_name)

    def set_device_enabled(self, device_name: str, enabled: bool) -> bool:
        return self._fluxy.client.device_set_device_enabled(device_name, enabled)

    # Ignition-style aliases for porting scripts.
    listDevices = list_devices
    addDevice = add_device
    removeDevice = remove_device
    setDeviceEnabled = set_device_enabled


class DbNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def get_connections(self) -> list[DatabaseConnection]:
        return self._fluxy.client.db_get_connections()

    def get_connection_info(self, name: str) -> dict[str, Any]:
        return self._fluxy.client.db_get_connection_info(name)

    def add_datasource(
        self,
        name: str,
        connect_url: str,
        *,
        jdbc_driver: str = "SQLite",
        description: str = "Fluxy-managed datasource",
        username: str = "",
        password: str = "",
        props: str = "",
        validation_query: str = "SELECT 1",
        max_connections: int = 8,
    ) -> bool:
        return self._fluxy.client.db_add_datasource(
            name,
            connect_url,
            jdbc_driver=jdbc_driver,
            description=description,
            username=username,
            password=password,
            props=props,
            validation_query=validation_query,
            max_connections=max_connections,
        )

    def remove_datasource(self, name: str) -> bool:
        return self._fluxy.client.db_remove_datasource(name)

    def set_datasource_connect_url(self, name: str, connect_url: str) -> bool:
        return self._fluxy.client.db_set_datasource_connect_url(name, connect_url)

    def set_datasource_enabled(self, name: str, enabled: bool) -> bool:
        return self._fluxy.client.db_set_datasource_enabled(name, enabled)

    def set_datasource_max_connections(self, name: str, max_connections: int) -> bool:
        return self._fluxy.client.db_set_datasource_max_connections(name, max_connections)

    def begin_transaction(
        self, database: str, isolation_level: int | None = None, timeout: int | None = None
    ) -> str:
        return self._fluxy.client.db_begin_transaction(database, isolation_level=isolation_level, timeout=timeout)

    def commit_transaction(self, tx: str) -> bool:
        return self._fluxy.client.db_commit_transaction(tx)

    def rollback_transaction(self, tx: str) -> bool:
        return self._fluxy.client.db_rollback_transaction(tx)

    def close_transaction(self, tx: str) -> bool:
        return self._fluxy.client.db_close_transaction(tx)

    def run_query(
        self, query: str, database: str | None = None, tx: str | None = None
    ) -> QueryResult:
        return self._fluxy.client.db_run_query(query, database=database, tx=tx)

    def run_scalar_query(
        self, query: str, database: str | None = None, args: list[Any] | None = None
    ) -> QueryResult:
        return self._fluxy.client.db_run_scalar_query(query, database=database, args=args)

    def run_scalar_prep_query(
        self, query: str, args: list[Any] | None = None, database: str | None = None
    ) -> Any:
        return self._fluxy.client.db_run_scalar_prep_query(query, args=args, database=database)

    def run_prep_query(
        self, query: str, args: list[Any] | None = None, database: str | None = None
    ) -> QueryResult:
        return self._fluxy.client.db_run_prep_query(query, args=args, database=database)

    def run_prep_update(
        self,
        query: str,
        args: list[Any] | None = None,
        database: str | None = None,
        *,
        get_key: bool = False,
        skip_audit: bool = False,
    ) -> Any:
        return self._fluxy.client.db_run_prep_update(
            query,
            args=args,
            database=database,
            get_key=get_key,
            skip_audit=skip_audit,
        )

    def run_update_query(
        self,
        query: str,
        database: str | None = None,
        tx: str | None = None,
        *,
        get_key: bool = False,
        skip_audit: bool = False,
    ) -> Any:
        return self._fluxy.client.db_run_update_query(
            query,
            database=database,
            tx=tx,
            get_key=get_key,
            skip_audit=skip_audit,
        )

    def run_named_query(
        self,
        path: str,
        parameters: dict[str, Any] | None = None,
        project: str | None = None,
        *,
        runner: NamedQueryRunner | None = None,
        use_gateway: bool = False,
    ) -> Any:
        selected_runner = runner if runner is not None else self._fluxy.named_query_runner
        if selected_runner is not None and not use_gateway:
            return selected_runner.run_named_query(
                self._fluxy.require_project_location(),
                path,
                parameters=parameters,
                project=project,
            )
        return self._fluxy.client.db_run_named_query(path, parameters=parameters, project=project)

    # Ignition-style aliases for porting scripts.
    getConnections = get_connections
    getConnectionInfo = get_connection_info
    addDatasource = add_datasource
    setDatasourceConnectURL = set_datasource_connect_url
    setDatasourceEnabled = set_datasource_enabled
    setDatasourceMaxConnections = set_datasource_max_connections
    removeDatasource = remove_datasource
    beginTransaction = begin_transaction
    commitTransaction = commit_transaction
    rollbackTransaction = rollback_transaction
    closeTransaction = close_transaction
    runQuery = run_query
    runScalarQuery = run_scalar_query
    runScalarPrepQuery = run_scalar_prep_query
    runPrepQuery = run_prep_query
    runPrepUpdate = run_prep_update
    runUpdateQuery = run_update_query
    runNamedQuery = run_named_query


class HistorianNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def browse(
        self,
        path: str,
        continuation_point: str | None = None,
    ) -> list[HistorianBrowseResult]:
        return self._fluxy.client.historian_browse(
            path,
            continuation_point=continuation_point,
        )

    def store_data_points(
        self,
        paths: list[str],
        values: list[Any],
        timestamps: list[int],
        qualities: list[int | str] | None = None,
    ) -> list[str]:
        return self._fluxy.client.historian_store_data_points(
            paths, values, timestamps=timestamps, qualities=qualities
        )

    def query_raw_points(
        self, paths: list[str], start_time: int, end_time: int, return_size: int = 100
    ) -> QueryResult:
        return self._fluxy.client.historian_query_raw_points(
            paths, start_time, end_time, return_size=return_size
        )

    def query_aggregated_points(
        self,
        paths: list[str],
        start_time: int,
        end_time: int,
        aggregates: list[str] | None = None,
        fill_modes: list[str] | None = None,
        column_names: list[str] | None = None,
        return_format: str = "WIDE",
        return_size: int = 1,
        include_bounds: bool = False,
        exclude_observations: bool = False,
    ) -> QueryResult:
        return self._fluxy.client.historian_query_aggregated_points(
            paths,
            start_time,
            end_time,
            aggregates=aggregates,
            fill_modes=fill_modes,
            column_names=column_names,
            return_format=return_format,
            return_size=return_size,
            include_bounds=include_bounds,
            exclude_observations=exclude_observations,
        )

    def store_annotations(
        self,
        paths: list[str],
        start_times: list[int],
        end_times: list[int] | None = None,
        types: list[str] | None = None,
        data: list[str] | None = None,
        storage_ids: list[str] | None = None,
        deleted: list[bool] | None = None,
    ) -> list[str]:
        return self._fluxy.client.historian_store_annotations(
            paths,
            start_times,
            end_times=end_times,
            types=types,
            data=data,
            storage_ids=storage_ids,
            deleted=deleted,
        )

    def query_annotations(
        self,
        paths: list[str],
        start_date: int,
        end_date: int | None = None,
        allowed_types: list[str] | None = None,
    ) -> list[HistorianAnnotation]:
        return self._fluxy.client.historian_query_annotations(
            paths,
            start_date,
            end_date=end_date,
            allowed_types=allowed_types,
        )

    def delete_annotations(self, paths: list[str], storage_ids: list[str]) -> list[str]:
        return self._fluxy.client.historian_delete_annotations(paths, storage_ids)

    def store_metadata(
        self,
        paths: list[str],
        timestamps: list[int],
        properties: dict[str, Any],
    ) -> list[str]:
        return self._fluxy.client.historian_store_metadata(paths, timestamps, properties)

    def query_metadata(
        self,
        paths: list[str],
        start_date: int | None = None,
        end_date: int | None = None,
    ) -> list[HistorianMetadata]:
        return self._fluxy.client.historian_query_metadata(
            paths,
            start_date=start_date,
            end_date=end_date,
        )

    storeDataPoints = store_data_points
    queryRawPoints = query_raw_points
    queryAggregatedPoints = query_aggregated_points
    storeAnnotations = store_annotations
    queryAnnotations = query_annotations
    deleteAnnotations = delete_annotations
    storeMetadata = store_metadata
    queryMetadata = query_metadata


class ReportNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def get_report_names_as_list(self, project: str) -> list[str]:
        return self._fluxy.client.report_get_names_as_list(project)

    def get_report_names_as_dataset(
        self, project: str, include_report_name: bool = True
    ) -> QueryResult:
        return self._fluxy.client.report_get_names_as_dataset(
            project,
            include_report_name=include_report_name,
        )

    def execute_report(
        self,
        path: str,
        project: str,
        parameters: dict[str, Any] | None = None,
        file_type: str = "pdf",
    ) -> ReportExecutionResult:
        return self._fluxy.client.report_execute_report(
            path,
            project,
            parameters=parameters,
            file_type=file_type,
        )

    getReportNamesAsList = get_report_names_as_list
    getReportNamesAsDataset = get_report_names_as_dataset
    executeReport = execute_report


class UserNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def get_user_sources(self) -> list[dict[str, Any]]:
        return self._fluxy.client.user_get_user_sources()

    def get_roles(self, user_source: str) -> list[str]:
        return self._fluxy.client.user_get_roles(user_source)

    def add_role(self, user_source: str, role: str) -> UserResponse:
        return self._fluxy.client.user_add_role(user_source, role)

    def edit_role(self, user_source: str, old_name: str, new_name: str) -> UserResponse:
        return self._fluxy.client.user_edit_role(user_source, old_name, new_name)

    def remove_role(self, user_source: str, role: str) -> UserResponse:
        return self._fluxy.client.user_remove_role(user_source, role)

    def add_user(
        self,
        user_source: str,
        username: str,
        password: str,
        fields: dict[str, Any] | None = None,
        roles: list[str] | None = None,
        contact_info: dict[str, str] | None = None,
    ) -> UserResponse:
        return self._fluxy.client.user_add_user(
            user_source,
            username,
            password,
            fields=fields,
            roles=roles,
            contact_info=contact_info,
        )

    def get_user(self, user_source: str, username: str) -> dict[str, Any]:
        return self._fluxy.client.user_get_user(user_source, username)

    def get_users(self, user_source: str) -> list[dict[str, Any]]:
        return self._fluxy.client.user_get_users(user_source)

    def edit_user(
        self,
        user_source: str,
        username: str,
        fields: dict[str, Any] | None = None,
        roles: list[str] | None = None,
        contact_info: dict[str, str] | None = None,
        password: str | None = None,
    ) -> UserResponse:
        return self._fluxy.client.user_edit_user(
            user_source,
            username,
            fields=fields,
            roles=roles,
            contact_info=contact_info,
            password=password,
        )

    def remove_user(self, user_source: str, username: str) -> UserResponse:
        return self._fluxy.client.user_remove_user(user_source, username)

    def add_schedule(
        self, name: str, source_schedule: str = "Always", description: str | None = None
    ) -> UserResponse:
        return self._fluxy.client.user_add_schedule(name, source_schedule, description)

    def get_schedule(self, name: str) -> dict[str, Any]:
        return self._fluxy.client.user_get_schedule(name)

    def get_schedules(self) -> list[dict[str, Any]]:
        return self._fluxy.client.user_get_schedules()

    def remove_schedule(self, name: str) -> UserResponse:
        return self._fluxy.client.user_remove_schedule(name)

    def add_holiday(self, name: str, date: int, repeat_annually: bool = False) -> UserResponse:
        return self._fluxy.client.user_add_holiday(name, date, repeat_annually)

    def get_holiday(self, name: str) -> dict[str, Any]:
        return self._fluxy.client.user_get_holiday(name)

    def get_holidays(self) -> list[dict[str, Any]]:
        return self._fluxy.client.user_get_holidays()

    def remove_holiday(self, name: str) -> UserResponse:
        return self._fluxy.client.user_remove_holiday(name)

    getUserSources = get_user_sources
    getRoles = get_roles
    addRole = add_role
    editRole = edit_role
    removeRole = remove_role
    addUser = add_user
    getUser = get_user
    getUsers = get_users
    editUser = edit_user
    removeUser = remove_user
    addSchedule = add_schedule
    getSchedule = get_schedule
    getSchedules = get_schedules
    removeSchedule = remove_schedule
    addHoliday = add_holiday
    getHoliday = get_holiday
    getHolidays = get_holidays
    removeHoliday = remove_holiday


class UtilNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def get_version(self, *, refresh: bool = False) -> IgnitionVersion:
        return self._fluxy.client.util_get_version(refresh=refresh)

    def refresh_version(self) -> IgnitionVersion:
        return self._fluxy.client.util_get_version(refresh=True)

    def get_modules(self) -> QueryResult:
        return self._fluxy.client.util_get_modules()

    def get_gateway_status(
        self,
        gateway_address: str,
        connect_timeout_millis: int | None = None,
        socket_timeout_millis: int | None = None,
        bypass_cert_validation: bool | None = None,
    ) -> str:
        return self._fluxy.client.util_get_gateway_status(
            gateway_address,
            connect_timeout_millis=connect_timeout_millis,
            socket_timeout_millis=socket_timeout_millis,
            bypass_cert_validation=bypass_cert_validation,
        )

    def get_project_name(self) -> str:
        return self._fluxy.client.util_get_project_name()

    def audit(
        self,
        action: str,
        action_target: str | None = None,
        action_value: str | None = None,
        audit_profile: str | None = None,
        actor: str | None = None,
        actor_host: str | None = None,
        originating_system: list[str] | str | None = None,
        event_timestamp: int | None = None,
        originating_context: int | None = None,
        status_code: int | None = None,
    ) -> bool:
        return self._fluxy.client.util_audit(
            action,
            action_target=action_target,
            action_value=action_value,
            audit_profile=audit_profile,
            actor=actor,
            actor_host=actor_host,
            originating_system=originating_system,
            event_timestamp=event_timestamp,
            originating_context=originating_context,
            status_code=status_code,
        )

    def query_audit_log(
        self,
        audit_profile_name: str,
        start_date: int | None = None,
        end_date: int | None = None,
        actor_filter: str | None = None,
        action_filter: str | None = None,
        target_filter: str | None = None,
        value_filter: str | None = None,
        system_filter: str | None = None,
        context_filter: int | None = None,
    ) -> QueryResult:
        return self._fluxy.client.util_query_audit_log(
            audit_profile_name,
            start_date=start_date,
            end_date=end_date,
            actor_filter=actor_filter,
            action_filter=action_filter,
            target_filter=target_filter,
            value_filter=value_filter,
            system_filter=system_filter,
            context_filter=context_filter,
        )

    getVersion = get_version
    getModules = get_modules
    getGatewayStatus = get_gateway_status
    getProjectName = get_project_name
    queryAuditLog = query_audit_log


class AlarmNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def query_status(
        self,
        priority: list[int | str] | None = None,
        state: list[int | str] | None = None,
        source: list[str] | None = None,
        include_shelved: bool = False,
        provider: list[str] | None = None,
    ) -> QueryResult:
        return self._fluxy.client.alarm_query_status(
            priority=priority,
            state=state,
            source=source,
            include_shelved=include_shelved,
            provider=provider,
        )

    def shelve(
        self,
        paths: list[str],
        timeout_seconds: int | None = None,
        timeout_minutes: int | None = None,
    ) -> bool:
        return self._fluxy.client.alarm_shelve(
            paths, timeout_seconds=timeout_seconds, timeout_minutes=timeout_minutes
        )

    def unshelve(self, paths: list[str]) -> bool:
        return self._fluxy.client.alarm_unshelve(paths)

    def get_shelved_paths(self) -> list[dict[str, Any]]:
        return self._fluxy.client.alarm_get_shelved_paths()

    def acknowledge(
        self, alarm_ids: list[str], notes: str | None = None, username: str = "fluxy"
    ) -> list[str]:
        return self._fluxy.client.alarm_acknowledge(alarm_ids, notes=notes, username=username)

    queryStatus = query_status
    getShelvedPaths = get_shelved_paths


class OpcNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def get_servers(self, include_disabled: bool = False) -> list[str]:
        return self._fluxy.client.opc_get_servers(include_disabled=include_disabled)

    def get_server_state(self, opc_server: str) -> str | None:
        return self._fluxy.client.opc_get_server_state(opc_server)

    def browse(
        self,
        opc_server: str | None = None,
        device: str | None = None,
        folder_path: str | None = None,
        opc_item_path: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._fluxy.client.opc_browse(
            opc_server=opc_server,
            device=device,
            folder_path=folder_path,
            opc_item_path=opc_item_path,
        )

    def browse_server(self, opc_server: str, node_id: str) -> list[dict[str, Any]]:
        return self._fluxy.client.opc_browse_server(opc_server, node_id)

    def browse_simple(
        self,
        opc_server: str | None = None,
        device: str | None = None,
        folder_path: str | None = None,
        opc_item_path: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._fluxy.client.opc_browse_simple(
            opc_server=opc_server,
            device=device,
            folder_path=folder_path,
            opc_item_path=opc_item_path,
        )

    def read_value(self, opc_server: str, item_path: str) -> OpcValue:
        return self._fluxy.client.opc_read_value(opc_server, item_path)

    def read_values(self, opc_server: str, item_paths: list[str]) -> list[OpcValue]:
        return self._fluxy.client.opc_read_values(opc_server, item_paths)

    def write_value(self, opc_server: str, item_path: str, value: Any) -> str:
        return self._fluxy.client.opc_write_value(opc_server, item_path, value)

    def write_values(self, opc_server: str, item_paths: list[str], values: list[Any]) -> list[str]:
        return self._fluxy.client.opc_write_values(opc_server, item_paths, values)

    getServers = get_servers
    getServerState = get_server_state
    browseServer = browse_server
    browseSimple = browse_simple
    readValue = read_value
    readValues = read_values
    writeValue = write_value
    writeValues = write_values


class OpcUaNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def add_connection(
        self,
        name: str,
        description: str,
        discovery_url: str,
        endpoint_url: str,
        security_policy: str = "None",
        security_mode: str = "None",
        settings: dict[str, Any] | None = None,
    ) -> bool:
        return self._fluxy.client.opcua_add_connection(
            name,
            description,
            discovery_url,
            endpoint_url,
            security_policy=security_policy,
            security_mode=security_mode,
            settings=settings,
        )

    def remove_connection(self, name: str) -> bool:
        return self._fluxy.client.opcua_remove_connection(name)

    addConnection = add_connection
    removeConnection = remove_connection


class NamedQueryNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def add_named_query(
        self,
        name: str,
        query: str,
        *,
        database: str = "",
        parameters: list[dict[str, Any]] | None = None,
    ) -> Path:
        return add_named_query(
            self._fluxy.require_project_location(),
            name,
            query,
            database=database,
            parameters=parameters,
        )

    def delete_named_query(self, name: str) -> Path:
        return delete_named_query(self._fluxy.require_project_location(), name)


class ScriptingNamespace:
    def __init__(self, fluxy: Fluxy) -> None:
        self._fluxy = fluxy

    def deploy_function_file(
        self,
        file_name: str,
        source: str | None = None,
        target_directory: str | Path | None = None,
    ) -> Path:
        project_location = self._fluxy.require_project_location()
        if source is None:
            return deploy_builtin_function_file(project_location, file_name, target_directory=target_directory)
        return deploy_function_file(project_location, file_name, source, target_directory=target_directory)

    def delete_function_file(self, file_name: str, target_directory: str | Path | None = None) -> Path:
        return delete_function_file(
            self._fluxy.require_project_location(),
            file_name,
            target_directory=target_directory,
        )

    def run_function_file(
        self,
        file_name: str,
        *args: Any,
        target_directory: str | Path | None = None,
        **kwargs: Any,
    ) -> ScriptRunResult:
        return self._fluxy.client.script_run_function_file(
            file_name,
            *args,
            target_directory=str(target_directory) if target_directory is not None else None,
            **kwargs,
        )
