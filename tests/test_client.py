import json

import httpx
import pytest

from fluxy import Fluxy, FluxyClient, FluxyError


class FakeNamedQueryRunner:
    def __init__(self, result=None):
        self.calls = []
        self.result = result if result is not None else [{"message": "Hello from plugin"}]

    def run_named_query(self, project_location, path, *, parameters=None, project=None):
        self.calls.append(
            {
                "project_location": project_location,
                "path": path,
                "parameters": parameters,
                "project": project,
            }
        )
        return self.result


def test_read_blocking_posts_tag_paths_and_returns_qualified_values():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/readBlocking"
        assert request.headers["authorization"] == "Bearer secret"
        assert request.read()
        return httpx.Response(
            200,
            json={
                "ok": True,
                "values": [
                    {
                        "tagPath": "[default]A/B",
                        "value": 12.3,
                        "quality": "Good",
                        "timestamp": "2026-05-11T12:00:00.000Z",
                    }
                ],
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        token="secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    values = client.read_blocking(["[default]A/B"], timeout_ms=45000)

    assert values[0].tag_path == "[default]A/B"
    assert values[0].value == 12.3
    assert values[0].quality == "Good"


def test_read_blocking_accepts_single_tag_path_string():
    def handler(request):
        assert json.loads(request.content) == {"tagPaths": ["[default]A/B"]}
        return httpx.Response(
            200,
            json={"ok": True, "values": [{"tagPath": "[default]A/B", "value": 1, "quality": "Good"}]},
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    value = client.read_blocking("[default]A/B")

    assert value.tag_path == "[default]A/B"
    assert value.value == 1


def test_write_blocking_posts_values_and_returns_quality_codes():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/writeBlocking"
        payload = httpx.Request("POST", request.url, content=request.content).read()
        assert payload
        return httpx.Response(
            200,
            json={
                "ok": True,
                "qualities": [{"tagPath": "[default]A/SP", "quality": "Good"}],
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    qualities = client.write_blocking(["[default]A/SP"], [42.0])

    assert qualities[0].tag_path == "[default]A/SP"
    assert qualities[0].quality == "Good"


def test_write_blocking_accepts_single_tag_path_string_and_single_value():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/writeBlocking"
        assert json.loads(request.content) == {"tagPaths": ["[default]A/SP"], "values": [42.0]}
        return httpx.Response(
            200,
            json={"ok": True, "qualities": [{"tagPath": "[default]A/SP", "quality": "Good"}]},
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    quality = client.write_blocking("[default]A/SP", 42.0)

    assert quality.tag_path == "[default]A/SP"
    assert quality.quality == "Good"


def test_write_blocking_rejects_mismatched_lengths():
    client = FluxyClient("https://ignition.example/system/webdev/Fluxy")

    with pytest.raises(ValueError):
        client.write_blocking(["[default]A/SP"], [])


def test_delete_tags_posts_tag_paths_and_returns_quality_codes():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/deleteTags"
        assert json.loads(request.content) == {"tagPaths": ["[default]A/SP"]}
        return httpx.Response(
            200,
            json={"ok": True, "qualities": [{"tagPath": "[default]A/SP", "quality": "Good"}]},
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    quality = client.delete_tags("[default]A/SP")

    assert quality.tag_path == "[default]A/SP"
    assert quality.quality == "Good"


def test_copy_posts_tag_paths_destination_and_returns_quality_codes():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/copy"
        assert json.loads(request.content) == {
            "tagPaths": ["[default]A/Source"],
            "destinationPath": "[default]B",
            "collisionPolicy": "o",
        }
        return httpx.Response(
            200,
            json={
                "ok": True,
                "qualities": [
                    {"tagPath": "[default]A/Source", "destinationPath": "[default]B", "quality": "Good"}
                ],
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.copy("[default]A/Source", "[default]B")

    assert result.tag_path == "[default]A/Source"
    assert result.destination_path == "[default]B"
    assert result.quality == "Good"


def test_device_list_devices_returns_device_connections():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/device/listDevices"
        assert json.loads(request.content) == {}
        return httpx.Response(
            200,
            json={
                "ok": True,
                "devices": [
                    {"Name": "Sim", "Enabled": True, "State": "Connected", "Driver": "Simulator"}
                ],
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    devices = client.device_list_devices()

    assert devices[0].name == "Sim"
    assert devices[0].enabled is True
    assert devices[0].state == "Connected"
    assert devices[0].driver == "Simulator"


def test_device_add_remove_and_enable_post_expected_payloads():
    seen_paths = []

    def handler(request):
        seen_paths.append(request.url.path)
        payload = json.loads(request.content)
        if request.url.path.endswith("/fluxy/device/addDevice"):
            assert payload == {
                "deviceType": "Simulator",
                "deviceName": "FluxyTempSimulator",
                "deviceProps": {"Enabled": 0},
                "description": "temporary",
            }
            return httpx.Response(200, json={"ok": True, "deviceName": "FluxyTempSimulator"})
        if request.url.path.endswith("/fluxy/device/setDeviceEnabled"):
            assert payload == {"deviceName": "FluxyTempSimulator", "enabled": False}
            return httpx.Response(200, json={"ok": True, "deviceName": "FluxyTempSimulator"})
        if request.url.path.endswith("/fluxy/device/removeDevice"):
            assert payload == {"deviceName": "FluxyTempSimulator"}
            return httpx.Response(200, json={"ok": True, "deviceName": "FluxyTempSimulator"})
        raise AssertionError("Unexpected path: %s" % request.url.path)

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.device_add_device(
        "Simulator",
        "FluxyTempSimulator",
        device_props={"Enabled": 0},
        description="temporary",
    )
    assert client.device_set_device_enabled("FluxyTempSimulator", False)
    assert client.device_remove_device("FluxyTempSimulator")
    assert seen_paths == [
        "/system/webdev/Fluxy/fluxy/device/addDevice",
        "/system/webdev/Fluxy/fluxy/device/setDeviceEnabled",
        "/system/webdev/Fluxy/fluxy/device/removeDevice",
    ]


def test_move_posts_source_and_destination_paths():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/move"
        assert json.loads(request.content) == {
            "sourcePath": "[default]A/OldTag",
            "destinationPath": "[default]B",
        }
        return httpx.Response(
            200,
            json={
                "ok": True,
                "quality": {
                    "sourcePath": "[default]A/OldTag",
                    "destinationPath": "[default]B",
                    "quality": "Good",
                },
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.move("[default]A/OldTag", "[default]B")

    assert result.source_path == "[default]A/OldTag"
    assert result.destination_path == "[default]B"
    assert result.quality == "Good"


def test_rename_posts_tag_path_and_new_name():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/rename"
        assert json.loads(request.content) == {"tagPath": "[default]A/OldTag", "newName": "NewTag"}
        return httpx.Response(
            200,
            json={"ok": True, "quality": {"tagPath": "[default]A/OldTag", "newName": "NewTag", "quality": "Good"}},
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.rename("[default]A/OldTag", "NewTag")

    assert result.tag_path == "[default]A/OldTag"
    assert result.new_name == "NewTag"
    assert result.quality == "Good"


def test_import_tags_posts_tags_base_path_and_collision_policy():
    exported_tags = {"tags": [{"name": "Imported", "tagType": "Folder"}]}

    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/importTags"
        assert json.loads(request.content) == {
            "tags": exported_tags,
            "basePath": "[default]",
            "collisionPolicy": "o",
        }
        return httpx.Response(200, json={"ok": True, "qualities": [{"quality": "Good"}]})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    results = client.import_tags(exported_tags, "[default]", collision_policy="o")

    assert results[0].quality == "Good"


def test_export_tags_posts_tag_paths_and_returns_exported_tags():
    exported_tags = {"tags": [{"name": "Exported", "tagType": "Folder"}]}

    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/exportTags"
        assert json.loads(request.content) == {"tagPaths": ["[default]Exported"], "recursive": True}
        return httpx.Response(200, json={"ok": True, "tags": exported_tags, "rawJson": json.dumps(exported_tags)})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.export_tags("[default]Exported")

    assert result.tags == exported_tags
    assert json.loads(result.raw_json) == exported_tags


def test_get_configuration_posts_path_and_returns_configs():
    configs = [{"name": "Configured", "tooltip": "hello Tooltip", "documentation": "Hello Description"}]

    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/getConfiguration"
        assert json.loads(request.content) == {"path": "[default]Configured", "recursive": False}
        return httpx.Response(200, json={"ok": True, "configs": configs})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.get_configuration("[default]Configured")

    assert result == configs


def test_configure_posts_base_path_tags_and_collision_policy():
    tag_config = {
        "name": "TestTag",
        "tagType": "AtomicTag",
        "valueSource": "memory",
        "dataType": "Float4",
        "value": 1.0,
    }

    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/configure"
        assert json.loads(request.content) == {
            "basePath": "[default]Folder",
            "tags": [tag_config],
            "collisionPolicy": "m",
        }
        return httpx.Response(
            200,
            json={"ok": True, "qualities": [{"name": "TestTag", "quality": "Good"}]},
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    qualities = client.configure("[default]Folder", [tag_config], collision_policy="m")

    assert qualities[0].name == "TestTag"
    assert qualities[0].quality == "Good"


def test_browse_posts_path_and_filter_and_returns_results():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/browse"
        assert json.loads(request.content) == {
            "path": "[default]Folder",
            "filter": {"tagType": "AtomicTag"},
        }
        return httpx.Response(
            200,
            json={
                "ok": True,
                "results": [
                    {
                        "name": "MemoryFloat",
                        "fullPath": "[default]Folder/MemoryFloat",
                        "tagType": "AtomicTag",
                        "dataType": "Float4",
                        "hasChildren": False,
                    }
                ],
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    results = client.browse("[default]Folder", tag_filter={"tagType": "AtomicTag"})

    assert results[0].name == "MemoryFloat"
    assert results[0].full_path == "[default]Folder/MemoryFloat"
    assert results[0].tag_type == "AtomicTag"
    assert results[0].data_type == "Float4"


def test_query_posts_provider_query_and_returns_results():
    query = {"condition": {"path": "Folder/*"}, "returnProperties": ["path", "tagType"]}

    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/queryTags"
        assert json.loads(request.content) == {"provider": "default", "query": query, "limit": 10}
        return httpx.Response(
            200,
            json={
                "ok": True,
                "results": [{"path": "Folder/Tag", "tagType": "AtomicTag"}],
                "continuationPoint": None,
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    results = client.query("default", query=query, limit=10)

    assert results == [{"path": "Folder/Tag", "tagType": "AtomicTag"}]
    assert results.continuation_point is None


def test_request_scan_posts_to_project_endpoint():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/project/requestScan"
        assert json.loads(request.content) == {}
        return httpx.Response(200, json={"ok": True, "message": "Project scan requested"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.request_scan()

    assert result.ok is True
    assert result.message == "Project scan requested"


def test_project_get_project_name_posts_to_project_endpoint():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/project/getProjectName"
        assert json.loads(request.content) == {}
        return httpx.Response(200, json={"ok": True, "projectName": "flux"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.project_get_project_name() == "flux"


def test_project_get_project_names_posts_to_project_endpoint():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/project/getProjectNames"
        assert json.loads(request.content) == {}
        return httpx.Response(200, json={"ok": True, "projectNames": ["flux", "other"]})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.project_get_project_names() == ["flux", "other"]


def test_historian_store_and_query_raw_points_post_expected_payloads():
    seen_paths = []

    def handler(request):
        seen_paths.append(request.url.path)
        payload = json.loads(request.content)
        if request.url.path.endswith("/fluxy/historian/storeDataPoints"):
            assert payload == {
                "paths": ["histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"],
                "values": [1.5],
                "timestamps": [1778545000000],
                "qualities": [192],
            }
            return httpx.Response(200, json={"ok": True, "qualities": ["Good"]})
        if request.url.path.endswith("/fluxy/historian/queryRawPoints"):
            assert payload == {
                "paths": ["histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"],
                "startTime": 1778544990000,
                "endTime": 1778545010000,
                "returnSize": 100,
            }
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "columns": ["path", "value", "quality", "timestamp"],
                        "rows": [["A", 1.5, "Good", 1778545000000]],
                    },
                },
            )
        raise AssertionError("Unexpected path: %s" % request.url.path)

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    path = "histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"

    assert client.historian_store_data_points([path], [1.5], [1778545000000], [192]) == ["Good"]
    rows = client.historian_query_raw_points([path], 1778544990000, 1778545010000)

    assert rows == [{"path": "A", "value": 1.5, "quality": "Good", "timestamp": 1778545000000}]
    assert seen_paths == [
        "/system/webdev/Fluxy/fluxy/historian/storeDataPoints",
        "/system/webdev/Fluxy/fluxy/historian/queryRawPoints",
    ]


def test_historian_query_aggregated_points_posts_expected_payload():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/historian/queryAggregatedPoints"
        assert json.loads(request.content) == {
            "paths": ["histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"],
            "startTime": 1778544990000,
            "endTime": 1778545010000,
            "returnFormat": "WIDE",
            "returnSize": 1,
            "includeBounds": False,
            "excludeObservations": False,
            "aggregates": ["Maximum"],
            "fillModes": ["NONE"],
            "columnNames": ["value"],
        }
        return httpx.Response(
            200,
            json={"ok": True, "result": {"columns": ["t_stamp", "value"], "rows": [[1, 30.0]]}},
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    rows = client.historian_query_aggregated_points(
        ["histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"],
        1778544990000,
        1778545010000,
        aggregates=["Maximum"],
        fill_modes=["NONE"],
        column_names=["value"],
    )

    assert rows == [{"t_stamp": 1, "value": 30.0}]


def test_historian_browse_posts_path_and_returns_results():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/historian/browse"
        assert json.loads(request.content) == {
            "path": "histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"
        }
        return httpx.Response(
            200,
            json={
                "ok": True,
                "results": [
                    {
                        "path": "histprov:Core Historian:/sys:gateway:/prov:default:/tag:A/B",
                        "displayPath": None,
                        "hasChildren": False,
                        "type": "tag",
                        "metadata": "ImmutablePropertySet[{}]",
                    }
                ],
                "continuationPoint": None,
                "quality": "Good",
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    results = client.historian_browse(
        "histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"
    )

    assert results[0].path.endswith("/tag:A/B")
    assert results[0].result_type == "tag"
    assert results[0].has_children is False


def test_historian_annotations_post_expected_payloads():
    seen_paths = []

    def handler(request):
        seen_paths.append(request.url.path)
        payload = json.loads(request.content)
        if request.url.path.endswith("/fluxy/historian/storeAnnotations"):
            assert payload == {
                "paths": ["histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"],
                "startTimes": [1778545000000],
                "endTimes": [1778545010000],
                "types": ["note"],
                "data": ["hello"],
            }
            return httpx.Response(200, json={"ok": True, "qualities": ["Good"]})
        if request.url.path.endswith("/fluxy/historian/queryAnnotations"):
            assert payload == {
                "paths": ["histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"],
                "startDate": 1778544990000,
                "endDate": 1778545020000,
                "allowedTypes": ["note"],
            }
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "annotations": [
                        {
                            "storageId": "annotation-id",
                            "path": "histprov:Core Historian:/sys:gateway:/prov:default:/tag:A",
                            "startTime": "2026-05-12T01:00:00Z",
                            "endTime": "2026-05-12T01:00:10Z",
                            "type": "note",
                            "data": "hello",
                            "author": "unknown",
                        }
                    ],
                },
            )
        if request.url.path.endswith("/fluxy/historian/deleteAnnotations"):
            assert payload == {
                "paths": ["histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"],
                "storageIds": ["annotation-id"],
            }
            return httpx.Response(200, json={"ok": True, "qualities": ["Good"]})
        raise AssertionError("Unexpected path: %s" % request.url.path)

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    path = "histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"

    assert client.historian_store_annotations(
        [path], [1778545000000], end_times=[1778545010000], types=["note"], data=["hello"]
    ) == ["Good"]
    annotations = client.historian_query_annotations(
        [path], 1778544990000, end_date=1778545020000, allowed_types=["note"]
    )
    assert annotations[0].storage_id == "annotation-id"
    assert annotations[0].data == "hello"
    assert client.historian_delete_annotations([path], ["annotation-id"]) == ["Good"]
    assert seen_paths == [
        "/system/webdev/Fluxy/fluxy/historian/storeAnnotations",
        "/system/webdev/Fluxy/fluxy/historian/queryAnnotations",
        "/system/webdev/Fluxy/fluxy/historian/deleteAnnotations",
    ]


def test_historian_metadata_post_expected_payloads():
    def handler(request):
        payload = json.loads(request.content)
        if request.url.path.endswith("/fluxy/historian/storeMetadata"):
            assert payload == {
                "paths": ["histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"],
                "timestamps": [1778545000000],
                "properties": {"documentation": "hello", "engUnit": "flux"},
            }
            return httpx.Response(200, json={"ok": True, "qualities": ["Good"]})
        if request.url.path.endswith("/fluxy/historian/queryMetadata"):
            assert payload == {
                "paths": ["histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"],
                "startDate": 1778544990000,
                "endDate": 1778545010000,
            }
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "metadata": [
                        {
                            "path": "histprov:Core Historian:/sys:gateway:/prov:default:/tag:A",
                            "timestamp": "2026-05-12T01:00:00Z",
                            "quality": "Good",
                            "properties": {"documentation": "hello", "engUnit": "flux"},
                        }
                    ],
                },
            )
        raise AssertionError("Unexpected path: %s" % request.url.path)

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    path = "histprov:Core Historian:/sys:gateway:/prov:default:/tag:A"

    assert client.historian_store_metadata(
        [path], [1778545000000], {"documentation": "hello", "engUnit": "flux"}
    ) == ["Good"]
    metadata = client.historian_query_metadata(
        [path], start_date=1778544990000, end_date=1778545010000
    )
    assert metadata[0].path == path
    assert metadata[0].properties == {"documentation": "hello", "engUnit": "flux"}


def test_util_diagnostics_post_expected_payloads():
    def handler(request):
        payload = json.loads(request.content)
        if request.url.path.endswith("/fluxy/util/getVersion"):
            assert payload == {}
            return httpx.Response(200, json={"ok": True, "version": "8.3.0", "major": 8, "minor": 3})
        if request.url.path.endswith("/fluxy/util/getModules"):
            assert payload == {}
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "columns": ["Id", "Name", "Version", "State", "License"],
                        "rows": [["mod", "Module", "1.0", "Running", "Trial"]],
                    },
                },
            )
        if request.url.path.endswith("/fluxy/util/getGatewayStatus"):
            assert payload == {
                "gatewayAddress": "localhost:8088",
                "connectTimeoutMillis": 1000,
                "socketTimeoutMillis": 2000,
                "bypassCertValidation": False,
            }
            return httpx.Response(200, json={"ok": True, "status": "RUNNING"})
        if request.url.path.endswith("/fluxy/util/getProjectName"):
            assert payload == {}
            return httpx.Response(200, json={"ok": True, "projectName": "flux"})
        if request.url.path.endswith("/fluxy/util/audit"):
            assert payload == {
                "action": "FluxyIntegrationAudit",
                "actionTarget": "target",
                "actionValue": "created",
                "auditProfile": "AuditLog",
                "actor": "fluxy",
            }
            return httpx.Response(200, json={"ok": True})
        if request.url.path.endswith("/fluxy/util/queryAuditLog"):
            assert payload == {
                "auditProfileName": "AuditLog",
                "startDate": 1778544990000,
                "endDate": 1778545010000,
                "actionFilter": "FluxyIntegrationAudit",
                "targetFilter": "target",
            }
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "columns": ["ACTION", "ACTION_TARGET", "ACTION_VALUE"],
                        "rows": [["FluxyIntegrationAudit", "target", "created"]],
                    },
                },
            )
        raise AssertionError("Unexpected path: %s" % request.url.path)

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    version = client.util_get_version()
    modules = client.util_get_modules()
    status = client.util_get_gateway_status(
        "localhost:8088",
        connect_timeout_millis=1000,
        socket_timeout_millis=2000,
        bypass_cert_validation=False,
    )
    project_name = client.util_get_project_name()
    audit_ok = client.util_audit(
        "FluxyIntegrationAudit",
        action_target="target",
        action_value="created",
        audit_profile="AuditLog",
        actor="fluxy",
    )
    audit_rows = client.util_query_audit_log(
        "AuditLog",
        start_date=1778544990000,
        end_date=1778545010000,
        action_filter="FluxyIntegrationAudit",
        target_filter="target",
    )

    assert version.version == "8.3.0"
    assert version.major == 8
    assert version.minor == 3
    assert modules == [{"Id": "mod", "Name": "Module", "Version": "1.0", "State": "Running", "License": "Trial"}]
    assert status == "RUNNING"
    assert project_name == "flux"
    assert audit_ok is True
    assert audit_rows == [
        {"ACTION": "FluxyIntegrationAudit", "ACTION_TARGET": "target", "ACTION_VALUE": "created"}
    ]


def test_util_get_version_caches_until_refresh():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={"ok": True, "version": "8.3.%d" % calls, "major": 8, "minor": 3},
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.util_get_version().version == "8.3.1"
    assert client.util_get_version().version == "8.3.1"
    assert client.util_get_version(refresh=True).version == "8.3.2"
    assert calls == 2


def test_report_methods_post_expected_payloads():
    def handler(request):
        payload = json.loads(request.content)
        if request.url.path.endswith("/fluxy/report/getReportNamesAsList"):
            assert payload == {"project": "flux"}
            return httpx.Response(200, json={"ok": True, "reports": ["test_Report"]})
        if request.url.path.endswith("/fluxy/report/getReportNamesAsDataset"):
            assert payload == {"project": "flux", "includeReportName": True}
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {"columns": ["Path", "Name"], "rows": [["test_Report", "test_Report"]]},
                },
            )
        if request.url.path.endswith("/fluxy/report/executeReport"):
            assert payload == {
                "path": "test_Report",
                "project": "flux",
                "parameters": {"marker": "hello"},
                "fileType": "pdf",
            }
            return httpx.Response(
                200,
                json={"ok": True, "contentBase64": "JVBERi0xLjQ=", "fileType": "pdf"},
            )
        raise AssertionError("Unexpected path: %s" % request.url.path)

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.report_get_names_as_list("flux") == ["test_Report"]
    assert client.report_get_names_as_dataset("flux") == [
        {"Path": "test_Report", "Name": "test_Report"}
    ]
    result = client.report_execute_report(
        "test_Report", "flux", parameters={"marker": "hello"}, file_type="pdf"
    )
    assert result.content == b"%PDF-1.4"
    assert result.file_type == "pdf"


def test_alarm_methods_post_expected_payloads():
    seen_paths = []

    def handler(request):
        seen_paths.append(request.url.path)
        payload = json.loads(request.content)
        if request.url.path.endswith("/fluxy/alarm/queryStatus"):
            assert payload == {"includeShelved": True, "source": ["prov:default:/tag:A:/alm:High"]}
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "columns": ["Source", "EventId", "State"],
                        "rows": [["prov:default:/tag:A:/alm:High", "event-id", "ActiveUnacked"]],
                    },
                },
            )
        if request.url.path.endswith("/fluxy/alarm/shelve"):
            assert payload == {"paths": ["prov:default:/tag:A:/alm:High"], "timeoutSeconds": 60}
            return httpx.Response(200, json={"ok": True})
        if request.url.path.endswith("/fluxy/alarm/getShelvedPaths"):
            assert payload == {}
            return httpx.Response(
                200,
                json={"ok": True, "results": [{"path": "prov:default:/tag:A:/alm:High"}]},
            )
        if request.url.path.endswith("/fluxy/alarm/unshelve"):
            assert payload == {"paths": ["prov:default:/tag:A:/alm:High"]}
            return httpx.Response(200, json={"ok": True})
        if request.url.path.endswith("/fluxy/alarm/acknowledge"):
            assert payload == {"alarmIds": ["event-id"], "username": "fluxy", "notes": "checked"}
            return httpx.Response(200, json={"ok": True, "failed": []})
        raise AssertionError("Unexpected path: %s" % request.url.path)

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    source = "prov:default:/tag:A:/alm:High"

    rows = client.alarm_query_status(source=[source], include_shelved=True)
    assert client.alarm_shelve([source], timeout_seconds=60)
    shelved = client.alarm_get_shelved_paths()
    assert client.alarm_unshelve([source])
    assert client.alarm_acknowledge(["event-id"], notes="checked") == []

    assert rows[0]["EventId"] == "event-id"
    assert shelved == [{"path": source}]
    assert seen_paths == [
        "/system/webdev/Fluxy/fluxy/alarm/queryStatus",
        "/system/webdev/Fluxy/fluxy/alarm/shelve",
        "/system/webdev/Fluxy/fluxy/alarm/getShelvedPaths",
        "/system/webdev/Fluxy/fluxy/alarm/unshelve",
        "/system/webdev/Fluxy/fluxy/alarm/acknowledge",
    ]


def test_opc_methods_post_expected_payloads():
    def handler(request):
        payload = json.loads(request.content)
        if request.url.path.endswith("/fluxy/opc/getServers"):
            assert payload == {"includeDisabled": True}
            return httpx.Response(200, json={"ok": True, "servers": ["Ignition OPC UA Server"]})
        if request.url.path.endswith("/fluxy/opc/getServerState"):
            assert payload == {"opcServer": "Ignition OPC UA Server"}
            return httpx.Response(200, json={"ok": True, "state": "CONNECTED"})
        if request.url.path.endswith("/fluxy/opc/browse"):
            assert payload == {"opcServer": "Ignition OPC UA Server", "device": "Sim"}
            return httpx.Response(200, json={"ok": True, "results": [{"opcItemPath": "[Sim]Path"}]})
        if request.url.path.endswith("/fluxy/opc/browseServer"):
            assert payload == {"opcServer": "Ignition OPC UA Server", "nodeId": "Devices"}
            return httpx.Response(200, json={"ok": True, "results": [{"nodeId": "[Sim]"}]})
        if request.url.path.endswith("/fluxy/opc/browseSimple"):
            assert payload == {
                "opcServer": "Ignition OPC UA Server",
                "device": "Sim",
                "folderPath": None,
                "opcItemPath": None,
            }
            return httpx.Response(200, json={"ok": True, "results": [{"opcItemPath": "[Sim]Path"}]})
        if request.url.path.endswith("/fluxy/opc/readValue"):
            assert payload == {"opcServer": "Ignition OPC UA Server", "itemPath": "[Sim]Path"}
            return httpx.Response(
                200, json={"ok": True, "value": 1, "quality": "Good", "timestamp": 1778545000000}
            )
        if request.url.path.endswith("/fluxy/opc/readValues"):
            assert payload == {"opcServer": "Ignition OPC UA Server", "itemPaths": ["[Sim]Path"]}
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "values": [{"value": 1, "quality": "Good", "timestamp": 1778545000000}],
                },
            )
        if request.url.path.endswith("/fluxy/opc/writeValue"):
            assert payload == {"opcServer": "Ignition OPC UA Server", "itemPath": "[Sim]Path", "value": 2}
            return httpx.Response(200, json={"ok": True, "quality": "Good"})
        if request.url.path.endswith("/fluxy/opc/writeValues"):
            assert payload == {
                "opcServer": "Ignition OPC UA Server",
                "itemPaths": ["[Sim]Path"],
                "values": [3],
            }
            return httpx.Response(200, json={"ok": True, "qualities": ["Good"]})
        raise AssertionError("Unexpected path: %s" % request.url.path)

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.opc_get_servers(include_disabled=True) == ["Ignition OPC UA Server"]
    assert client.opc_get_server_state("Ignition OPC UA Server") == "CONNECTED"
    assert client.opc_browse(opc_server="Ignition OPC UA Server", device="Sim") == [
        {"opcItemPath": "[Sim]Path"}
    ]
    assert client.opc_browse_server("Ignition OPC UA Server", "Devices") == [{"nodeId": "[Sim]"}]
    assert client.opc_browse_simple(opc_server="Ignition OPC UA Server", device="Sim") == [
        {"opcItemPath": "[Sim]Path"}
    ]
    assert client.opc_read_value("Ignition OPC UA Server", "[Sim]Path").quality == "Good"
    assert client.opc_read_values("Ignition OPC UA Server", ["[Sim]Path"])[0].quality == "Good"
    assert client.opc_write_value("Ignition OPC UA Server", "[Sim]Path", 2) == "Good"
    assert client.opc_write_values("Ignition OPC UA Server", ["[Sim]Path"], [3]) == ["Good"]


def test_db_get_connections_posts_and_returns_connections():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/getConnections"
        assert json.loads(request.content) == {}
        return httpx.Response(
            200,
            json={"ok": True, "connections": [{"name": "FluxyHello", "status": "Valid"}]},
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    connections = client.db_get_connections()

    assert connections[0].name == "FluxyHello"
    assert connections[0].status == "Valid"


def test_db_get_connection_info_posts_name_and_returns_info():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/getConnectionInfo"
        assert json.loads(request.content) == {"name": "FluxyTest"}
        return httpx.Response(
            200,
            json={
                "ok": True,
                "info": {
                    "name": "FluxyTest",
                    "status": "Valid",
                    "ConnectURL": "jdbc:sqlite:/tmp/test_datasource.sqlite3",
                },
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    info = client.db_get_connection_info("FluxyTest")

    assert info["name"] == "FluxyTest"
    assert info["status"] == "Valid"
    assert info["ConnectURL"] == "jdbc:sqlite:/tmp/test_datasource.sqlite3"


def test_db_add_datasource_posts_connection_details():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/addDatasource"
        assert json.loads(request.content) == {
            "jdbcDriver": "SQLite",
            "name": "FluxyTest",
            "description": "test datasource",
            "connectUrl": "jdbc:sqlite:/tmp/test_datasource.sqlite3",
            "username": "",
            "password": "",
            "props": "",
            "validationQuery": "SELECT 1",
            "maxConnections": 4,
        }
        return httpx.Response(200, json={"ok": True, "name": "FluxyTest"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.db_add_datasource(
        "FluxyTest",
        "jdbc:sqlite:/tmp/test_datasource.sqlite3",
        description="test datasource",
        max_connections=4,
    )


def test_db_set_datasource_connect_url_posts_name_and_url():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/setDatasourceConnectURL"
        assert json.loads(request.content) == {
            "name": "FluxyTest",
            "connectUrl": "jdbc:sqlite:/tmp/moved.sqlite3",
        }
        return httpx.Response(
            200,
            json={"ok": True, "name": "FluxyTest", "connectUrl": "jdbc:sqlite:/tmp/moved.sqlite3"},
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.db_set_datasource_connect_url("FluxyTest", "jdbc:sqlite:/tmp/moved.sqlite3")


def test_db_set_datasource_enabled_posts_name_and_enabled_state():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/setDatasourceEnabled"
        assert json.loads(request.content) == {"name": "FluxyTest", "enabled": False}
        return httpx.Response(200, json={"ok": True, "name": "FluxyTest", "enabled": False})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.db_set_datasource_enabled("FluxyTest", False)


def test_db_set_datasource_max_connections_posts_limits():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/setDatasourceMaxConnections"
        assert json.loads(request.content) == {"name": "FluxyTest", "maxConnections": 3}
        return httpx.Response(200, json={"ok": True, "name": "FluxyTest", "maxConnections": 3})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.db_set_datasource_max_connections("FluxyTest", 3)


def test_db_remove_datasource_posts_name():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/removeDatasource"
        assert json.loads(request.content) == {"name": "FluxyTest"}
        return httpx.Response(200, json={"ok": True, "name": "FluxyTest"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.db_remove_datasource("FluxyTest")


def test_db_transaction_lifecycle_posts_transaction_ids():
    requests = []

    def handler(request):
        requests.append((request.url.path, json.loads(request.content)))
        if request.url.path.endswith("/beginTransaction"):
            return httpx.Response(200, json={"ok": True, "tx": "tx-1"})
        return httpx.Response(200, json={"ok": True, "tx": "tx-1"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    tx = client.db_begin_transaction("FluxyHello", timeout=30)

    assert tx == "tx-1"
    assert client.db_commit_transaction(tx)
    assert client.db_rollback_transaction(tx)
    assert client.db_close_transaction(tx)
    assert requests == [
        ("/system/webdev/Fluxy/fluxy/db/beginTransaction", {"database": "FluxyHello", "timeout": 30}),
        ("/system/webdev/Fluxy/fluxy/db/commitTransaction", {"tx": "tx-1"}),
        ("/system/webdev/Fluxy/fluxy/db/rollbackTransaction", {"tx": "tx-1"}),
        ("/system/webdev/Fluxy/fluxy/db/closeTransaction", {"tx": "tx-1"}),
    ]


def test_db_run_query_posts_query_database_and_returns_rows():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/runQuery"
        assert json.loads(request.content) == {"query": "select id, message from hello", "database": "FluxyHello"}
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {"columns": ["id", "message"], "rows": [[1, "Hello from SQLite"]]},
                "resultSource": "ignition.dataset",
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.db_run_query("select id, message from hello", database="FluxyHello")

    assert result == [{"id": 1, "message": "Hello from SQLite"}]
    assert result.columns == ["id", "message"]


def test_db_run_scalar_query_posts_query_database_and_args():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/runScalarQuery"
        assert json.loads(request.content) == {
            "query": "select message from hello where id = ?",
            "database": "FluxyHello",
            "args": [1],
        }
        return httpx.Response(200, json={"ok": True, "value": "Hello from SQLite"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    value = client.db_run_scalar_query(
        "select message from hello where id = ?",
        database="FluxyHello",
        args=[1],
    )

    assert value == "Hello from SQLite"


def test_db_run_scalar_prep_query_posts_query_database_and_args():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/runScalarPrepQuery"
        assert json.loads(request.content) == {
            "query": "select ?",
            "database": "FluxyHello",
            "args": ["hello World"],
        }
        return httpx.Response(200, json={"ok": True, "value": "hello World"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    value = client.db_run_scalar_prep_query(
        "select ?",
        args=["hello World"],
        database="FluxyHello",
    )

    assert value == "hello World"


def test_db_run_prep_query_posts_query_database_and_args():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/runPrepQuery"
        assert json.loads(request.content) == {
            "query": "select id, message from hello where id = ?",
            "database": "FluxyHello",
            "args": [1],
        }
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {"columns": ["id", "message"], "rows": [[1, "Hello from SQLite"]]},
                "resultSource": "ignition.dataset",
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.db_run_prep_query(
        "select id, message from hello where id = ?",
        args=[1],
        database="FluxyHello",
    )

    assert result == [{"id": 1, "message": "Hello from SQLite"}]
    assert result.columns == ["id", "message"]
    assert result.source == "ignition.dataset"


def test_db_run_prep_update_posts_query_args_and_options():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/runPrepUpdate"
        assert json.loads(request.content) == {
            "query": "update hello set message = ? where id = ?",
            "database": "FluxyHello",
            "args": ["updated", 1],
            "getKey": False,
            "skipAudit": True,
        }
        return httpx.Response(200, json={"ok": True, "value": 1})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    value = client.db_run_prep_update(
        "update hello set message = ? where id = ?",
        args=["updated", 1],
        database="FluxyHello",
        skip_audit=True,
    )

    assert value == 1


def test_db_run_update_query_posts_query_database_and_options():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/runUpdateQuery"
        assert json.loads(request.content) == {
            "query": "update hello set message = 'updated' where id = 1",
            "database": "FluxyHello",
            "getKey": False,
            "skipAudit": True,
        }
        return httpx.Response(200, json={"ok": True, "value": 1})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    value = client.db_run_update_query(
        "update hello set message = 'updated' where id = 1",
        database="FluxyHello",
        skip_audit=True,
    )

    assert value == 1


def test_db_run_named_query_posts_path_project_and_parameters():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/runNamedQuery"
        assert json.loads(request.content) == {
            "path": "hello_world",
            "parameters": {"world": "Hello"},
            "project": "flux",
        }
        return httpx.Response(200, json={"ok": True, "result": [{"message": "Hello from SQLite"}]})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.db_run_named_query("hello_world", parameters={"world": "Hello"}, project="flux")

    assert result == [{"message": "Hello from SQLite"}]


def test_db_run_named_query_returns_multiple_row_objects():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/runNamedQuery"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "columns": ["id", "message"],
                    "rows": [
                        [1, "first"],
                        [2, "second"],
                    ],
                },
                "resultSource": "ignition.dataset",
                "resultMessage": "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings",
            },
        )

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.db_run_named_query("multi_row")

    assert result == [
        {"id": 1, "message": "first"},
        {"id": 2, "message": "second"},
    ]
    assert result.columns == ["id", "message"]
    assert result.source == "ignition.dataset"
    assert result.message == "Ignition Dataset serialized as columns/rows; Fluxy converted to row mappings"
    assert result.mappings() is result


def test_db_run_named_query_rejects_non_row_result_shape():
    def handler(request):
        return httpx.Response(200, json={"ok": True, "result": {"message": "not rows"}})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(FluxyError, match="list of row objects"):
        client.db_run_named_query("bad_shape")


def test_fluxy_named_query_runner_handles_run_named_query(tmp_path):
    runner = FakeNamedQueryRunner()
    fx = Fluxy(
        "https://ignition.example/system/webdev/Fluxy",
        project_location=tmp_path,
        named_query_runner=runner,
    )

    result = fx.db.run_named_query("hello_world", parameters={"world": "Hello"}, project="flux")

    assert result == [{"message": "Hello from plugin"}]
    assert runner.calls == [
        {
            "project_location": tmp_path.resolve(),
            "path": "hello_world",
            "parameters": {"world": "Hello"},
            "project": "flux",
        }
    ]


def test_run_named_query_query_level_runner_overrides_fluxy_default(tmp_path):
    default_runner = FakeNamedQueryRunner(result=[{"message": "default"}])
    query_runner = FakeNamedQueryRunner(result=[{"message": "query"}])
    fx = Fluxy(
        "https://ignition.example/system/webdev/Fluxy",
        project_location=tmp_path,
        named_query_runner=default_runner,
    )

    result = fx.db.run_named_query("hello_world", runner=query_runner)

    assert result == [{"message": "query"}]
    assert default_runner.calls == []
    assert query_runner.calls[0]["path"] == "hello_world"


def test_run_named_query_can_force_gateway_when_default_runner_exists(tmp_path):
    runner = FakeNamedQueryRunner()

    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/db/runNamedQuery"
        return httpx.Response(200, json={"ok": True, "result": [{"message": "gateway"}]})

    fx = Fluxy(
        "https://ignition.example/system/webdev/Fluxy",
        project_location=tmp_path,
        named_query_runner=runner,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = fx.db.run_named_query("hello_world", use_gateway=True)

    assert result == [{"message": "gateway"}]
    assert runner.calls == []


def test_scripting_run_function_file_posts_args_and_kwargs():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/scripting/runFunctionFile"
        assert json.loads(request.content) == {
            "fileName": "hello_world.py",
            "args": [1],
            "kwargs": {"name": "Sam"},
        }
        return httpx.Response(200, json={"ok": True, "result": "Hello World!"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.script_run_function_file("hello_world.py", 1, name="Sam")

    assert result.ok is True
    assert result.result == "Hello World!"


def test_scripting_run_function_file_posts_target_directory():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/scripting/runFunctionFile"
        assert json.loads(request.content) == {
            "fileName": "hello_world.py",
            "args": [],
            "kwargs": {},
            "targetDirectory": "scratch",
        }
        return httpx.Response(200, json={"ok": True, "result": "Hello World!"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.script_run_function_file("hello_world.py", target_directory="scratch")

    assert result.ok is True


def test_fluxy_scripting_namespace_uses_configured_client():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/scripting/runFunctionFile"
        return httpx.Response(200, json={"ok": True, "result": "Hello World!"})

    fx = Fluxy(
        base_url="https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = fx.scripting.run_function_file("hello_world.py")

    assert result.ok is True
    assert result.result == "Hello World!"


def test_fluxy_tag_namespace_uses_configured_client():
    def handler(request):
        return httpx.Response(200, json={"ok": True, "values": [{"value": 1, "quality": "Good"}]})

    fx = Fluxy(
        base_url="https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    values = fx.tag.read_blocking(["[default]A/B"])

    assert values[0].value == 1


def test_fluxy_project_namespace_uses_configured_client():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/project/requestScan"
        return httpx.Response(200, json={"ok": True, "message": "Project scan requested"})

    fx = Fluxy(
        base_url="https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = fx.project.request_scan()

    assert result.ok is True


def test_fluxy_db_namespace_uses_configured_client():
    def handler(request):
        if request.url.path.endswith("/fluxy/db/getConnections"):
            return httpx.Response(200, json={"ok": True, "connections": [{"name": "FluxyHello", "status": "Valid"}]})
        if request.url.path.endswith("/fluxy/db/getConnectionInfo"):
            return httpx.Response(200, json={"ok": True, "info": {"name": "FluxyTest", "status": "Valid"}})
        if request.url.path.endswith("/fluxy/db/addDatasource"):
            return httpx.Response(200, json={"ok": True, "name": "FluxyTest"})
        if request.url.path.endswith("/fluxy/db/setDatasourceConnectURL"):
            return httpx.Response(200, json={"ok": True, "name": "FluxyTest"})
        if request.url.path.endswith("/fluxy/db/setDatasourceEnabled"):
            return httpx.Response(200, json={"ok": True, "name": "FluxyTest", "enabled": False})
        if request.url.path.endswith("/fluxy/db/setDatasourceMaxConnections"):
            return httpx.Response(200, json={"ok": True, "name": "FluxyTest", "maxConnections": 3})
        if request.url.path.endswith("/fluxy/db/removeDatasource"):
            return httpx.Response(200, json={"ok": True, "name": "FluxyTest"})
        raise AssertionError("Unexpected path: %s" % request.url.path)

    fx = Fluxy(
        base_url="https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    connections = fx.db.get_connections()

    assert connections[0].name == "FluxyHello"
    assert fx.db.get_connection_info("FluxyTest")["name"] == "FluxyTest"
    assert fx.db.add_datasource("FluxyTest", "jdbc:sqlite:/tmp/test_datasource.sqlite3")
    assert fx.db.set_datasource_connect_url("FluxyTest", "jdbc:sqlite:/tmp/moved.sqlite3")
    assert fx.db.set_datasource_enabled("FluxyTest", False)
    assert fx.db.set_datasource_max_connections("FluxyTest", 3)
    assert fx.db.remove_datasource("FluxyTest")


def test_ignition_style_aliases_remain_available():
    def handler(request):
        if request.url.path.endswith("/fluxy/tag/readBlocking"):
            return httpx.Response(200, json={"ok": True, "values": [{"value": 1, "quality": "Good"}]})
        if request.url.path.endswith("/fluxy/tag/writeBlocking"):
            return httpx.Response(200, json={"ok": True, "qualities": [{"quality": "Good"}]})
        if request.url.path.endswith("/fluxy/tag/deleteTags"):
            return httpx.Response(200, json={"ok": True, "qualities": [{"quality": "Good"}]})
        if request.url.path.endswith("/fluxy/tag/copy"):
            return httpx.Response(200, json={"ok": True, "qualities": [{"quality": "Good"}]})
        if request.url.path.endswith("/fluxy/tag/queryTags"):
            return httpx.Response(200, json={"ok": True, "results": [{"path": "A/B"}]})
        if request.url.path.endswith("/fluxy/db/getConnections"):
            return httpx.Response(200, json={"ok": True, "connections": [{"name": "FluxyHello", "status": "Valid"}]})
        if request.url.path.endswith("/fluxy/db/getConnectionInfo"):
            return httpx.Response(200, json={"ok": True, "info": {"name": "FluxyTest", "status": "Valid"}})
        if request.url.path.endswith("/fluxy/db/addDatasource"):
            return httpx.Response(200, json={"ok": True, "name": "FluxyTest"})
        if request.url.path.endswith("/fluxy/db/setDatasourceConnectURL"):
            return httpx.Response(200, json={"ok": True, "name": "FluxyTest"})
        if request.url.path.endswith("/fluxy/db/setDatasourceEnabled"):
            return httpx.Response(200, json={"ok": True, "name": "FluxyTest", "enabled": False})
        if request.url.path.endswith("/fluxy/db/setDatasourceMaxConnections"):
            return httpx.Response(200, json={"ok": True, "name": "FluxyTest", "maxConnections": 3})
        if request.url.path.endswith("/fluxy/db/removeDatasource"):
            return httpx.Response(200, json={"ok": True, "name": "FluxyTest"})
        if request.url.path.endswith("/fluxy/db/beginTransaction"):
            return httpx.Response(200, json={"ok": True, "tx": "tx-1"})
        if request.url.path.endswith("/fluxy/db/commitTransaction"):
            return httpx.Response(200, json={"ok": True, "tx": "tx-1"})
        if request.url.path.endswith("/fluxy/db/rollbackTransaction"):
            return httpx.Response(200, json={"ok": True, "tx": "tx-1"})
        if request.url.path.endswith("/fluxy/db/closeTransaction"):
            return httpx.Response(200, json={"ok": True, "tx": "tx-1"})
        if request.url.path.endswith("/fluxy/db/runQuery"):
            return httpx.Response(200, json={"ok": True, "result": [{"message": "Hello from SQLite"}]})
        if request.url.path.endswith("/fluxy/db/runScalarQuery"):
            return httpx.Response(200, json={"ok": True, "value": "Hello from SQLite"})
        if request.url.path.endswith("/fluxy/db/runScalarPrepQuery"):
            return httpx.Response(200, json={"ok": True, "value": "hello World"})
        if request.url.path.endswith("/fluxy/db/runPrepQuery"):
            return httpx.Response(200, json={"ok": True, "result": [{"message": "Hello from SQLite"}]})
        if request.url.path.endswith("/fluxy/db/runPrepUpdate"):
            return httpx.Response(200, json={"ok": True, "value": 1})
        if request.url.path.endswith("/fluxy/db/runUpdateQuery"):
            return httpx.Response(200, json={"ok": True, "value": 1})
        if request.url.path.endswith("/fluxy/db/runNamedQuery"):
            return httpx.Response(200, json={"ok": True, "result": [{"message": "Hello from SQLite"}]})
        if request.url.path.endswith("/fluxy/device/listDevices"):
            return httpx.Response(
                200,
                json={"ok": True, "devices": [{"Name": "Sim", "Enabled": True, "State": "Running"}]},
            )
        if request.url.path.endswith("/fluxy/device/addDevice"):
            return httpx.Response(200, json={"ok": True, "deviceName": "Sim"})
        if request.url.path.endswith("/fluxy/device/setDeviceEnabled"):
            return httpx.Response(200, json={"ok": True, "deviceName": "Sim", "enabled": False})
        if request.url.path.endswith("/fluxy/device/removeDevice"):
            return httpx.Response(200, json={"ok": True, "deviceName": "Sim"})
        if request.url.path.endswith("/fluxy/project/requestScan"):
            return httpx.Response(200, json={"ok": True, "message": "Project scan requested"})
        if request.url.path.endswith("/fluxy/project/getProjectName"):
            return httpx.Response(200, json={"ok": True, "projectName": "flux"})
        if request.url.path.endswith("/fluxy/project/getProjectNames"):
            return httpx.Response(200, json={"ok": True, "projectNames": ["flux"]})
        raise AssertionError("Unexpected path: %s" % request.url.path)

    fx = Fluxy(
        base_url="https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert fx.tag.readBlocking("[default]A/B").quality == "Good"
    assert fx.tag.writeBlocking("[default]A/B", 1).quality == "Good"
    assert fx.tag.deleteTags("[default]A/B").quality == "Good"
    assert fx.tag.copy("[default]A/B", "[default]C").quality == "Good"
    assert fx.tag.query("default") == [{"path": "A/B"}]
    assert fx.db.getConnections()[0].name == "FluxyHello"
    assert fx.db.getConnectionInfo("FluxyTest")["name"] == "FluxyTest"
    assert fx.db.addDatasource("FluxyTest", "jdbc:sqlite:/tmp/test_datasource.sqlite3")
    assert fx.db.setDatasourceConnectURL("FluxyTest", "jdbc:sqlite:/tmp/moved.sqlite3")
    assert fx.db.setDatasourceEnabled("FluxyTest", False)
    assert fx.db.setDatasourceMaxConnections("FluxyTest", 3)
    assert fx.db.removeDatasource("FluxyTest")
    tx = fx.db.beginTransaction("FluxyHello")
    assert tx == "tx-1"
    assert fx.db.commitTransaction(tx)
    assert fx.db.rollbackTransaction(tx)
    assert fx.db.closeTransaction(tx)
    assert fx.db.runQuery("select message from hello") == [{"message": "Hello from SQLite"}]
    assert fx.db.runScalarQuery("select message from hello", database="FluxyHello") == "Hello from SQLite"
    assert fx.db.runScalarPrepQuery("select ?", ["hello World"]) == "hello World"
    assert fx.db.runPrepQuery("select message from hello where id = ?", [1]) == [
        {"message": "Hello from SQLite"}
    ]
    assert fx.db.runPrepUpdate("update hello set message = ?", ["updated"]) == 1
    assert fx.db.runUpdateQuery("update hello set message = 'updated'") == 1
    assert fx.db.runNamedQuery("hello_world") == [{"message": "Hello from SQLite"}]
    assert fx.device.listDevices()[0].name == "Sim"
    assert fx.device.addDevice("Simulator", "Sim", {"Enabled": 0})
    assert fx.device.setDeviceEnabled("Sim", False)
    assert fx.device.removeDevice("Sim")
    assert fx.project.requestScan().ok is True
    assert fx.project.getProjectName() == "flux"
    assert fx.project.getProjectNames() == ["flux"]


def test_fluxy_tag_provider_supplies_default_configure_base_path():
    tag_config = {"name": "Folder", "tagType": "Folder"}

    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/tag/configure"
        assert json.loads(request.content) == {
            "basePath": "[default]",
            "tags": [tag_config],
            "collisionPolicy": "o",
        }
        return httpx.Response(200, json={"ok": True, "qualities": [{"name": "Folder", "quality": "Good"}]})

    fx = Fluxy(
        base_url="https://ignition.example/system/webdev/Fluxy",
        tag_provider="default",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    results = fx.tag.configure([tag_config])

    assert results[0].quality == "Good"


def test_fluxy_project_location_enables_scripting_deploy(tmp_path):
    fx = Fluxy("https://ignition.example/system/webdev/Fluxy", project_location=tmp_path)

    path = fx.scripting.deploy_function_file("custom_hello.py", "def custom_hello():\n    return 'Hi'\n")

    assert path.exists()
    assert path.read_text() == "def custom_hello():\n    return 'Hi'\n"


def test_fluxy_project_location_enables_scripting_delete(tmp_path):
    fx = Fluxy("https://ignition.example/system/webdev/Fluxy", project_location=tmp_path)
    path = fx.scripting.deploy_function_file("hello_world.py", target_directory="scratch")

    deleted_path = fx.scripting.delete_function_file("hello_world.py", target_directory="scratch")

    assert deleted_path == path.parent
    assert not deleted_path.exists()


def test_fluxy_requires_project_location_for_scripting_deploy():
    fx = Fluxy("https://ignition.example/system/webdev/Fluxy")

    with pytest.raises(FluxyError, match="project_location is required"):
        fx.scripting.deploy_function_file("hello_world.py")


def test_bridge_error_raises_fluxy_error():
    def handler(request):
        return httpx.Response(200, json={"ok": False, "error": "nope"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(FluxyError, match="nope"):
        client.read_blocking(["[default]A/B"])


def test_non_json_bridge_response_raises_fluxy_error():
    def handler(request):
        return httpx.Response(200, text="")

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(FluxyError, match="non-JSON response"):
        client.read_blocking(["[default]A/B"])
