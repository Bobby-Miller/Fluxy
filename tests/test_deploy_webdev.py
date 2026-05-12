import json

from fluxy.deploy_webdev import deploy


def test_deploy_webdev_writes_namespaced_resources(tmp_path):
    written = deploy(tmp_path)
    resource_root = tmp_path / "com.inductiveautomation.webdev" / "resources" / "fluxy"

    assert written
    assert (resource_root / "tag" / "readBlocking" / "doPost.py").exists()
    assert (resource_root / "tag" / "writeBlocking" / "doPost.py").exists()
    assert (resource_root / "tag" / "deleteTags" / "doPost.py").exists()
    assert not (resource_root / "tag" / "exists").exists()
    assert (resource_root / "tag" / "copy" / "doPost.py").exists()
    assert (resource_root / "tag" / "move" / "doPost.py").exists()
    assert (resource_root / "tag" / "rename" / "doPost.py").exists()
    assert (resource_root / "tag" / "importTags" / "doPost.py").exists()
    assert (resource_root / "tag" / "exportTags" / "doPost.py").exists()
    assert (resource_root / "tag" / "getConfiguration" / "doPost.py").exists()
    assert (resource_root / "tag" / "configure" / "doPost.py").exists()
    assert (resource_root / "tag" / "browse" / "doPost.py").exists()
    assert (resource_root / "tag" / "queryTags" / "doPost.py").exists()
    assert (resource_root / "alarm" / "queryStatus" / "doPost.py").exists()
    assert (resource_root / "alarm" / "shelve" / "doPost.py").exists()
    assert (resource_root / "alarm" / "unshelve" / "doPost.py").exists()
    assert (resource_root / "alarm" / "getShelvedPaths" / "doPost.py").exists()
    assert (resource_root / "alarm" / "acknowledge" / "doPost.py").exists()
    assert (resource_root / "opc" / "getServers" / "doPost.py").exists()
    assert (resource_root / "opc" / "getServerState" / "doPost.py").exists()
    assert (resource_root / "opc" / "browse" / "doPost.py").exists()
    assert (resource_root / "opc" / "browseServer" / "doPost.py").exists()
    assert (resource_root / "opc" / "browseSimple" / "doPost.py").exists()
    assert (resource_root / "opc" / "readValue" / "doPost.py").exists()
    assert (resource_root / "opc" / "readValues" / "doPost.py").exists()
    assert (resource_root / "opc" / "writeValue" / "doPost.py").exists()
    assert (resource_root / "opc" / "writeValues" / "doPost.py").exists()
    assert (resource_root / "db" / "getConnections" / "doPost.py").exists()
    assert (resource_root / "db" / "getConnectionInfo" / "doPost.py").exists()
    assert (resource_root / "db" / "addDatasource" / "doPost.py").exists()
    assert (resource_root / "db" / "setDatasourceConnectURL" / "doPost.py").exists()
    assert (resource_root / "db" / "setDatasourceEnabled" / "doPost.py").exists()
    assert (resource_root / "db" / "setDatasourceMaxConnections" / "doPost.py").exists()
    assert (resource_root / "db" / "removeDatasource" / "doPost.py").exists()
    assert (resource_root / "db" / "beginTransaction" / "doPost.py").exists()
    assert (resource_root / "db" / "commitTransaction" / "doPost.py").exists()
    assert (resource_root / "db" / "rollbackTransaction" / "doPost.py").exists()
    assert (resource_root / "db" / "closeTransaction" / "doPost.py").exists()
    assert (resource_root / "db" / "runQuery" / "doPost.py").exists()
    assert (resource_root / "db" / "runScalarQuery" / "doPost.py").exists()
    assert (resource_root / "db" / "runScalarPrepQuery" / "doPost.py").exists()
    assert (resource_root / "db" / "runPrepQuery" / "doPost.py").exists()
    assert (resource_root / "db" / "runPrepUpdate" / "doPost.py").exists()
    assert (resource_root / "db" / "runUpdateQuery" / "doPost.py").exists()
    assert (resource_root / "db" / "runNamedQuery" / "doPost.py").exists()
    assert (resource_root / "device" / "listDevices" / "doPost.py").exists()
    assert (resource_root / "device" / "addDevice" / "doPost.py").exists()
    assert (resource_root / "device" / "removeDevice" / "doPost.py").exists()
    assert (resource_root / "device" / "setDeviceEnabled" / "doPost.py").exists()
    assert not (resource_root / "device" / "getDeviceHostname").exists()
    assert (resource_root / "project" / "requestScan" / "doPost.py").exists()
    assert (resource_root / "project" / "getProjectName" / "doPost.py").exists()
    assert (resource_root / "project" / "getProjectNames" / "doPost.py").exists()
    assert (resource_root / "historian" / "browse" / "doPost.py").exists()
    assert (resource_root / "historian" / "storeDataPoints" / "doPost.py").exists()
    assert (resource_root / "historian" / "queryRawPoints" / "doPost.py").exists()
    assert (resource_root / "historian" / "queryAggregatedPoints" / "doPost.py").exists()
    assert (resource_root / "historian" / "storeAnnotations" / "doPost.py").exists()
    assert (resource_root / "historian" / "queryAnnotations" / "doPost.py").exists()
    assert (resource_root / "historian" / "deleteAnnotations" / "doPost.py").exists()
    assert (resource_root / "historian" / "storeMetadata" / "doPost.py").exists()
    assert (resource_root / "historian" / "queryMetadata" / "doPost.py").exists()
    assert (resource_root / "util" / "getVersion" / "doPost.py").exists()
    assert (resource_root / "util" / "getModules" / "doPost.py").exists()
    assert (resource_root / "util" / "getGatewayStatus" / "doPost.py").exists()
    assert (resource_root / "util" / "getProjectName" / "doPost.py").exists()
    assert (resource_root / "util" / "audit" / "doPost.py").exists()
    assert (resource_root / "util" / "queryAuditLog" / "doPost.py").exists()
    assert (resource_root / "report" / "getReportNamesAsList" / "doPost.py").exists()
    assert (resource_root / "report" / "getReportNamesAsDataset" / "doPost.py").exists()
    assert (resource_root / "report" / "executeReport" / "doPost.py").exists()
    assert (resource_root / "user" / "getUserSources" / "doPost.py").exists()
    assert (resource_root / "user" / "getRoles" / "doPost.py").exists()
    assert (resource_root / "user" / "addRole" / "doPost.py").exists()
    assert (resource_root / "user" / "editRole" / "doPost.py").exists()
    assert (resource_root / "user" / "removeRole" / "doPost.py").exists()
    assert (resource_root / "user" / "addUser" / "doPost.py").exists()
    assert (resource_root / "user" / "getUser" / "doPost.py").exists()
    assert (resource_root / "user" / "getUsers" / "doPost.py").exists()
    assert (resource_root / "user" / "editUser" / "doPost.py").exists()
    assert (resource_root / "user" / "removeUser" / "doPost.py").exists()
    assert (resource_root / "user" / "addSchedule" / "doPost.py").exists()
    assert (resource_root / "user" / "getSchedules" / "doPost.py").exists()
    assert (resource_root / "user" / "removeSchedule" / "doPost.py").exists()
    assert (resource_root / "user" / "addHoliday" / "doPost.py").exists()
    assert (resource_root / "user" / "getHolidays" / "doPost.py").exists()
    assert (resource_root / "user" / "removeHoliday" / "doPost.py").exists()
    assert (resource_root / "scripting" / "runFunctionFile" / "doPost.py").exists()

    read_script = (resource_root / "tag" / "readBlocking" / "doPost.py").read_text()
    assert "def doPost" not in read_script
    assert "system.tag.readBlocking" in read_script

    delete_script = (resource_root / "tag" / "deleteTags" / "doPost.py").read_text()
    assert "system.tag.deleteTags" in delete_script

    copy_script = (resource_root / "tag" / "copy" / "doPost.py").read_text()
    assert "system.tag.copy" in copy_script

    move_script = (resource_root / "tag" / "move" / "doPost.py").read_text()
    assert "system.tag.move" in move_script

    rename_script = (resource_root / "tag" / "rename" / "doPost.py").read_text()
    assert "system.tag.rename" in rename_script

    import_script = (resource_root / "tag" / "importTags" / "doPost.py").read_text()
    assert "system.tag.importTags" in import_script

    export_script = (resource_root / "tag" / "exportTags" / "doPost.py").read_text()
    assert "system.tag.exportTags" in export_script

    get_configuration_script = (resource_root / "tag" / "getConfiguration" / "doPost.py").read_text()
    assert "system.tag.getConfiguration" in get_configuration_script

    query_script = (resource_root / "tag" / "queryTags" / "doPost.py").read_text()
    assert "system.tag.query" in query_script

    alarm_query_script = (resource_root / "alarm" / "queryStatus" / "doPost.py").read_text()
    assert "system.alarm.queryStatus" in alarm_query_script

    alarm_shelve_script = (resource_root / "alarm" / "shelve" / "doPost.py").read_text()
    assert "system.alarm.shelve" in alarm_shelve_script

    alarm_unshelve_script = (resource_root / "alarm" / "unshelve" / "doPost.py").read_text()
    assert "system.alarm.unshelve" in alarm_unshelve_script

    alarm_shelved_paths_script = (
        resource_root / "alarm" / "getShelvedPaths" / "doPost.py"
    ).read_text()
    assert "system.alarm.getShelvedPaths" in alarm_shelved_paths_script

    alarm_acknowledge_script = (resource_root / "alarm" / "acknowledge" / "doPost.py").read_text()
    assert "system.alarm.acknowledge" in alarm_acknowledge_script

    opc_get_servers_script = (resource_root / "opc" / "getServers" / "doPost.py").read_text()
    assert "system.opc.getServers" in opc_get_servers_script

    opc_get_server_state_script = (
        resource_root / "opc" / "getServerState" / "doPost.py"
    ).read_text()
    assert "system.opc.getServerState" in opc_get_server_state_script

    opc_browse_script = (resource_root / "opc" / "browse" / "doPost.py").read_text()
    assert "system.opc.browse" in opc_browse_script

    opc_browse_server_script = (resource_root / "opc" / "browseServer" / "doPost.py").read_text()
    assert "system.opc.browseServer" in opc_browse_server_script

    opc_browse_simple_script = (resource_root / "opc" / "browseSimple" / "doPost.py").read_text()
    assert "system.opc.browseSimple" in opc_browse_simple_script

    opc_read_value_script = (resource_root / "opc" / "readValue" / "doPost.py").read_text()
    assert "system.opc.readValue" in opc_read_value_script

    opc_read_values_script = (resource_root / "opc" / "readValues" / "doPost.py").read_text()
    assert "system.opc.readValues" in opc_read_values_script

    opc_write_value_script = (resource_root / "opc" / "writeValue" / "doPost.py").read_text()
    assert "system.opc.writeValue" in opc_write_value_script

    opc_write_values_script = (resource_root / "opc" / "writeValues" / "doPost.py").read_text()
    assert "system.opc.writeValues" in opc_write_values_script

    db_connections_script = (resource_root / "db" / "getConnections" / "doPost.py").read_text()
    assert "system.db.getConnections" in db_connections_script

    connection_info_script = (resource_root / "db" / "getConnectionInfo" / "doPost.py").read_text()
    assert "system.db.getConnectionInfo" in connection_info_script

    add_datasource_script = (resource_root / "db" / "addDatasource" / "doPost.py").read_text()
    assert "system.db.addDatasource" in add_datasource_script

    set_datasource_connect_url_script = (
        resource_root / "db" / "setDatasourceConnectURL" / "doPost.py"
    ).read_text()
    assert "system.db.setDatasourceConnectURL" in set_datasource_connect_url_script

    set_datasource_enabled_script = (
        resource_root / "db" / "setDatasourceEnabled" / "doPost.py"
    ).read_text()
    assert "system.db.setDatasourceEnabled" in set_datasource_enabled_script

    set_datasource_max_connections_script = (
        resource_root / "db" / "setDatasourceMaxConnections" / "doPost.py"
    ).read_text()
    assert "system.db.setDatasourceMaxConnections" in set_datasource_max_connections_script

    remove_datasource_script = (resource_root / "db" / "removeDatasource" / "doPost.py").read_text()
    assert "system.db.removeDatasource" in remove_datasource_script

    begin_transaction_script = (resource_root / "db" / "beginTransaction" / "doPost.py").read_text()
    assert "system.db.beginTransaction" in begin_transaction_script

    commit_transaction_script = (resource_root / "db" / "commitTransaction" / "doPost.py").read_text()
    assert "system.db.commitTransaction" in commit_transaction_script

    rollback_transaction_script = (resource_root / "db" / "rollbackTransaction" / "doPost.py").read_text()
    assert "system.db.rollbackTransaction" in rollback_transaction_script

    close_transaction_script = (resource_root / "db" / "closeTransaction" / "doPost.py").read_text()
    assert "system.db.closeTransaction" in close_transaction_script

    run_query_script = (resource_root / "db" / "runQuery" / "doPost.py").read_text()
    assert "system.db.runQuery" in run_query_script

    scalar_query_script = (resource_root / "db" / "runScalarQuery" / "doPost.py").read_text()
    assert "system.db.runScalarQuery" in scalar_query_script

    scalar_prep_query_script = (
        resource_root / "db" / "runScalarPrepQuery" / "doPost.py"
    ).read_text()
    assert "system.db.runScalarPrepQuery" in scalar_prep_query_script

    prep_query_script = (resource_root / "db" / "runPrepQuery" / "doPost.py").read_text()
    assert "system.db.runPrepQuery" in prep_query_script
    assert "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings" in prep_query_script

    prep_update_script = (resource_root / "db" / "runPrepUpdate" / "doPost.py").read_text()
    assert "system.db.runPrepUpdate" in prep_update_script

    update_query_script = (resource_root / "db" / "runUpdateQuery" / "doPost.py").read_text()
    assert "system.db.runUpdateQuery" in update_query_script

    named_query_script = (resource_root / "db" / "runNamedQuery" / "doPost.py").read_text()
    assert "system.db.runNamedQuery" in named_query_script
    assert "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings" in named_query_script

    list_devices_script = (resource_root / "device" / "listDevices" / "doPost.py").read_text()
    assert "system.device.listDevices" in list_devices_script

    add_device_script = (resource_root / "device" / "addDevice" / "doPost.py").read_text()
    assert "system.device.addDevice" in add_device_script

    remove_device_script = (resource_root / "device" / "removeDevice" / "doPost.py").read_text()
    assert "system.device.removeDevice" in remove_device_script

    set_device_enabled_script = (
        resource_root / "device" / "setDeviceEnabled" / "doPost.py"
    ).read_text()
    assert "system.device.setDeviceEnabled" in set_device_enabled_script

    get_project_name_script = (resource_root / "project" / "getProjectName" / "doPost.py").read_text()
    assert "system.project.getProjectName" in get_project_name_script

    get_project_names_script = (resource_root / "project" / "getProjectNames" / "doPost.py").read_text()
    assert "system.project.getProjectNames" in get_project_names_script

    historian_browse_script = (resource_root / "historian" / "browse" / "doPost.py").read_text()
    assert "system.historian.browse" in historian_browse_script
    assert "system.tag.browseHistoricalTags" in historian_browse_script

    store_data_points_script = (resource_root / "historian" / "storeDataPoints" / "doPost.py").read_text()
    assert "system.historian.storeDataPoints" in store_data_points_script
    assert "system.tag.storeTagHistory" in store_data_points_script

    query_raw_points_script = (resource_root / "historian" / "queryRawPoints" / "doPost.py").read_text()
    assert "system.historian.queryRawPoints" in query_raw_points_script
    assert "system.tag.queryTagHistory" in query_raw_points_script

    query_aggregated_points_script = (
        resource_root / "historian" / "queryAggregatedPoints" / "doPost.py"
    ).read_text()
    assert "system.historian.queryAggregatedPoints" in query_aggregated_points_script
    assert "system.tag.queryTagHistory" in query_aggregated_points_script

    store_annotations_script = (resource_root / "historian" / "storeAnnotations" / "doPost.py").read_text()
    assert "system.historian.storeAnnotations" in store_annotations_script
    assert "system.tag.storeAnnotations" in store_annotations_script

    query_annotations_script = (resource_root / "historian" / "queryAnnotations" / "doPost.py").read_text()
    assert "system.historian.queryAnnotations" in query_annotations_script
    assert "system.tag.queryAnnotations" in query_annotations_script

    delete_annotations_script = (resource_root / "historian" / "deleteAnnotations" / "doPost.py").read_text()
    assert "system.historian.deleteAnnotations" in delete_annotations_script
    assert "system.tag.deleteAnnotations" in delete_annotations_script

    store_metadata_script = (resource_root / "historian" / "storeMetadata" / "doPost.py").read_text()
    assert "system.historian.storeMetadata" in store_metadata_script

    query_metadata_script = (resource_root / "historian" / "queryMetadata" / "doPost.py").read_text()
    assert "system.historian.queryMetadata" in query_metadata_script

    util_get_version_script = (resource_root / "util" / "getVersion" / "doPost.py").read_text()
    assert "system.util.getVersion" in util_get_version_script

    util_get_modules_script = (resource_root / "util" / "getModules" / "doPost.py").read_text()
    assert "system.util.getModules" in util_get_modules_script

    util_get_gateway_status_script = (
        resource_root / "util" / "getGatewayStatus" / "doPost.py"
    ).read_text()
    assert "system.util.getGatewayStatus" in util_get_gateway_status_script

    util_get_project_name_script = (resource_root / "util" / "getProjectName" / "doPost.py").read_text()
    assert "system.util.getProjectName" in util_get_project_name_script

    util_audit_script = (resource_root / "util" / "audit" / "doPost.py").read_text()
    assert "system.util.audit" in util_audit_script

    util_query_audit_log_script = (resource_root / "util" / "queryAuditLog" / "doPost.py").read_text()
    assert "system.util.queryAuditLog" in util_query_audit_log_script

    report_names_list_script = (resource_root / "report" / "getReportNamesAsList" / "doPost.py").read_text()
    assert "system.report.getReportNamesAsList" in report_names_list_script

    report_names_dataset_script = (
        resource_root / "report" / "getReportNamesAsDataset" / "doPost.py"
    ).read_text()
    assert "system.report.getReportNamesAsDataset" in report_names_dataset_script

    report_execute_script = (resource_root / "report" / "executeReport" / "doPost.py").read_text()
    assert "system.report.executeReport" in report_execute_script

    user_get_sources_script = (resource_root / "user" / "getUserSources" / "doPost.py").read_text()
    assert "system.user.getUserSources" in user_get_sources_script

    user_add_script = (resource_root / "user" / "addUser" / "doPost.py").read_text()
    assert "system.user.addUser" in user_add_script

    user_edit_role_script = (resource_root / "user" / "editRole" / "doPost.py").read_text()
    assert "system.user.editRole" in user_edit_role_script

    user_remove_script = (resource_root / "user" / "removeUser" / "doPost.py").read_text()
    assert "system.user.removeUser" in user_remove_script

    user_add_schedule_script = (resource_root / "user" / "addSchedule" / "doPost.py").read_text()
    assert "system.user.addSchedule" in user_add_schedule_script

    user_add_holiday_script = (resource_root / "user" / "addHoliday" / "doPost.py").read_text()
    assert "system.user.addHoliday" in user_add_holiday_script

    scripting_script = (resource_root / "scripting" / "runFunctionFile" / "doPost.py").read_text()
    assert "exec source in namespace" in scripting_script
    assert str(tmp_path) in scripting_script

    resource_json = json.loads((resource_root / "tag" / "readBlocking" / "resource.json").read_text())
    assert "doPost.py" in resource_json["files"]
