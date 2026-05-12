import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


@pytest.mark.integration
def test_store_and_query_raw_historian_points_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    path_prefix = os.getenv(
        "FLUXY_HISTORIAN_TEST_PATH_PREFIX",
        "histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration",
    ).rstrip("/")
    history_path = path_prefix + "/" + uuid4().hex
    base_millis = int(time.time() * 1000) - 60_000
    timestamps = [base_millis, base_millis + 1_000, base_millis + 2_000]
    values = [12.5, 13.5, 14.5]

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        qualities = fx.historian.store_data_points(
            [history_path, history_path, history_path],
            values,
            timestamps=timestamps,
            qualities=[192, 192, 192],
        )
        rows = eventually_query_values(
            fx,
            history_path,
            start_time=base_millis - 5_000,
            end_time=base_millis + 10_000,
        )
        browse_results = eventually_browse_path(fx, path_prefix, history_path)
    except FluxyError as exc:
        pytest.fail("Fluxy historian integration failed: %s\nhistory_path=%s" % (exc, history_path))

    assert all(quality.startswith("Good") for quality in qualities), qualities
    assert any(result.path == history_path for result in browse_results)
    returned_values = [float(row["value"]) for row in rows if "value" in row]
    for expected in values:
        assert expected in returned_values


@pytest.mark.integration
def test_store_and_query_backfilled_historian_points_for_2024_and_2025():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    path_prefix = os.getenv(
        "FLUXY_HISTORIAN_TEST_PATH_PREFIX",
        "histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration",
    ).rstrip("/")
    history_path = path_prefix + "/Backfill/" + uuid4().hex
    samples = [
        (millis_utc(2024, 2, 3, 4, 5, 6), 24.203),
        (millis_utc(2024, 11, 12, 13, 14, 15), 24.912),
        (millis_utc(2025, 1, 7, 8, 9, 10), 25.107),
        (millis_utc(2025, 10, 21, 22, 23, 24), 25.821),
    ]
    timestamps = [sample[0] for sample in samples]
    values = [sample[1] for sample in samples]

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        qualities = fx.historian.store_data_points(
            [history_path for _sample in samples],
            values,
            timestamps=timestamps,
            qualities=[192 for _sample in samples],
        )
        assert all(quality.startswith("Good") for quality in qualities), qualities
        rows_by_timestamp = {
            timestamp: eventually_query_exact_window(fx, history_path, timestamp, value)
            for timestamp, value in samples
        }
    except FluxyError as exc:
        pytest.fail("Fluxy historian backfill integration failed: %s\nhistory_path=%s" % (exc, history_path))

    assert set(rows_by_timestamp) == set(timestamps)


@pytest.mark.integration
def test_query_aggregated_historian_points_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    path_prefix = os.getenv(
        "FLUXY_HISTORIAN_TEST_PATH_PREFIX",
        "histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration",
    ).rstrip("/")
    history_path = path_prefix + "/Aggregated/" + uuid4().hex
    base_millis = int(time.time() * 1000) - 60_000
    timestamps = [base_millis, base_millis + 10_000, base_millis + 20_000]

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        qualities = fx.historian.store_data_points(
            [history_path, history_path, history_path],
            [10.0, 20.0, 30.0],
            timestamps=timestamps,
            qualities=[192, 192, 192],
        )
        rows = eventually_query_aggregated_maximum(
            fx, history_path, base_millis - 10_000, base_millis + 30_000, 30.0
        )
    except FluxyError as exc:
        pytest.fail("Fluxy historian aggregated integration failed: %s\nhistory_path=%s" % (exc, history_path))

    assert all(quality.startswith("Good") for quality in qualities), qualities
    assert rows
    assert float(rows[0]["Maximum"]) == pytest.approx(30.0)


@pytest.mark.integration
def test_store_query_and_delete_historian_annotation_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    path_prefix = os.getenv(
        "FLUXY_HISTORIAN_TEST_PATH_PREFIX",
        "histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration",
    ).rstrip("/")
    history_path = path_prefix + "/Annotation/" + uuid4().hex
    marker = "fluxy-annotation-" + uuid4().hex
    base_millis = int(time.time() * 1000) - 60_000
    start_time = base_millis - 10_000
    end_time = base_millis + 10_000

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        point_qualities = fx.historian.store_data_points(
            [history_path], [42.25], timestamps=[base_millis], qualities=[192]
        )
        annotation_qualities = fx.historian.store_annotations(
            [history_path], [start_time], end_times=[end_time], types=["note"], data=[marker]
        )
        annotation = eventually_query_annotation(
            fx, history_path, start_time - 60_000, end_time + 60_000, marker
        )
        delete_qualities = fx.historian.delete_annotations([history_path], [annotation.storage_id])
        eventually_assert_annotation_deleted(
            fx, history_path, start_time - 60_000, end_time + 60_000, annotation.storage_id
        )
    except FluxyError as exc:
        pytest.fail("Fluxy historian annotation integration failed: %s\nhistory_path=%s" % (exc, history_path))

    assert all(quality.startswith("Good") for quality in point_qualities), point_qualities
    assert all(quality.startswith("Good") for quality in annotation_qualities), annotation_qualities
    assert all(quality.startswith("Good") for quality in delete_qualities), delete_qualities
    assert annotation.path == history_path
    assert annotation.data == marker


@pytest.mark.integration
def test_store_and_query_historian_metadata_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    path_prefix = os.getenv(
        "FLUXY_HISTORIAN_TEST_PATH_PREFIX",
        "histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration",
    ).rstrip("/")
    history_path = path_prefix + "/Metadata/" + uuid4().hex
    marker = "fluxy-metadata-" + uuid4().hex
    timestamp = int(time.time() * 1000) - 60_000

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        point_qualities = fx.historian.store_data_points(
            [history_path], [84.5], timestamps=[timestamp], qualities=[192]
        )
        metadata_qualities = fx.historian.store_metadata(
            [history_path],
            [timestamp],
            {"documentation": marker, "engUnit": "flux"},
        )
        metadata = eventually_query_metadata(
            fx, history_path, timestamp - 60_000, timestamp + 60_000, marker
        )
    except FluxyError as exc:
        pytest.fail("Fluxy historian metadata integration failed: %s\nhistory_path=%s" % (exc, history_path))

    assert all(quality.startswith("Good") for quality in point_qualities), point_qualities
    assert all(quality.startswith("Good") for quality in metadata_qualities), metadata_qualities
    assert metadata.path == history_path
    assert metadata.properties is not None
    assert metadata.properties.get("documentation") == marker
    assert metadata.properties.get("engUnit") == "flux"


@pytest.mark.integration
def test_configured_tag_values_define_historian_datatype_boundaries():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    path_prefix = os.getenv(
        "FLUXY_HISTORIAN_TEST_PATH_PREFIX",
        "histprov:Core Historian:/sys:gateway:/prov:default:/tag:FluxyHistorianIntegration",
    ).rstrip("/")
    root_folder = "FluxyHistorianTypeBoundary_%s" % uuid4().hex
    root_path = join_tag_path(provider_path.rstrip("/"), root_folder)
    history_prefix = path_prefix + "/TypeBoundary/" + uuid4().hex
    timestamp = int(time.time() * 1000) - 60_000
    supported_cases = [
        ("BooleanTag", "Boolean", True, 1.0),
        ("Int4Tag", "Int4", 7, 7.0),
        ("Int8Tag", "Int8", 1234567890123, 1234567890123.0),
        ("Float8Tag", "Float8", 7.75, 7.75),
        ("DateTimeTag", "DateTime", 1778545000000, 1778545000000.0),
    ]
    string_case = ("StringTag", "String", "hello-history")
    document_case = ("DocumentTag", "Document", {"a": 1, "nested": {"b": True}})
    tag_configs = [
        {
            "name": name,
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": data_type,
            "value": value,
        }
        for name, data_type, value, _expected in supported_cases
    ]
    tag_configs.extend(
        [
            {
                "name": string_case[0],
                "tagType": "AtomicTag",
                "valueSource": "memory",
                "dataType": string_case[1],
                "value": string_case[2],
            },
            {
                "name": document_case[0],
                "tagType": "AtomicTag",
                "valueSource": "memory",
                "dataType": document_case[1],
                "value": document_case[2],
            },
        ]
    )
    tag_paths = [join_tag_path(root_path, config["name"]) for config in tag_configs]

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        configure_results = fx.tag.configure(
            [{"name": root_folder, "tagType": "Folder", "tags": tag_configs}],
            base_path=provider_path.rstrip("/"),
            collision_policy="o",
        )
        read_values = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
        supported_qualities = []
        supported_rows = {}
        for index, (_name, data_type, _tag_value, expected_history_value) in enumerate(supported_cases):
            history_path = history_prefix + "/" + data_type
            qualities = fx.historian.store_data_points(
                [history_path], [read_values[index].value], timestamps=[timestamp + index], qualities=[192]
            )
            supported_qualities.extend(qualities)
            supported_rows[data_type] = eventually_query_history_value(
                fx, history_path, timestamp + index, expected_history_value
            )

        string_index = len(supported_cases)
        string_history_path = history_prefix + "/String"
        string_qualities = fx.historian.store_data_points(
            [string_history_path],
            [read_values[string_index].value],
            timestamps=[timestamp + string_index],
            qualities=[192],
        )
        string_rows = query_rows_for_short_boundary_window(
            fx, string_history_path, timestamp + string_index
        )

        document_index = len(supported_cases) + 1
        with pytest.raises(FluxyError):
            fx.historian.store_data_points(
                [history_prefix + "/Document"],
                [read_values[document_index].value],
                timestamps=[timestamp + document_index],
                qualities=[192],
            )
    except FluxyError as exc:
        pytest.fail("Fluxy tag/history datatype boundary integration failed: %s" % exc)
    finally:
        try:
            fx.tag.delete_tags([root_path])
        except FluxyError:
            pass

    assert all(result.quality.startswith("Good") for result in configure_results), configure_results
    assert all(value.quality.startswith("Good") for value in read_values), read_values
    assert all(quality.startswith("Good") for quality in supported_qualities), supported_qualities
    assert set(supported_rows) == {case[1] for case in supported_cases}
    assert all(quality.startswith("Good") for quality in string_qualities), string_qualities
    assert string_rows == []


def eventually_query_values(fx, history_path, start_time, end_time):
    deadline = time.monotonic() + float(os.getenv("FLUXY_HISTORIAN_TIMEOUT_SECONDS", "20"))
    last_rows = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_rows = fx.historian.query_raw_points(
                [history_path], start_time, end_time, return_size=100
            )
            if len(last_rows) >= 3:
                return last_rows
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Historian query did not return stored points: path=%r last_rows=%r last_error=%s"
        % (history_path, last_rows, last_error)
    )


def eventually_browse_path(fx, browse_path, expected_path):
    deadline = time.monotonic() + float(os.getenv("FLUXY_HISTORIAN_TIMEOUT_SECONDS", "20"))
    last_results = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_results = fx.historian.browse(browse_path)
            if any(result.path == expected_path for result in last_results):
                return last_results
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Historian browse did not return stored path: browse_path=%r expected=%r last_results=%r last_error=%s"
        % (browse_path, expected_path, last_results, last_error)
    )


def eventually_query_annotation(fx, history_path, start_time, end_time, marker):
    deadline = time.monotonic() + float(os.getenv("FLUXY_HISTORIAN_TIMEOUT_SECONDS", "20"))
    last_annotations = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_annotations = fx.historian.query_annotations(
                [history_path], start_time, end_date=end_time, allowed_types=["note"]
            )
            for annotation in last_annotations:
                if annotation.data == marker:
                    return annotation
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Historian queryAnnotations did not return stored annotation: path=%r marker=%r last_annotations=%r last_error=%s"
        % (history_path, marker, last_annotations, last_error)
    )


def eventually_query_aggregated_maximum(fx, history_path, start_time, end_time, expected_value):
    deadline = time.monotonic() + float(os.getenv("FLUXY_HISTORIAN_TIMEOUT_SECONDS", "20"))
    last_rows = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_rows = fx.historian.query_aggregated_points(
                [history_path],
                start_time,
                end_time,
                aggregates=["Maximum"],
                fill_modes=["NONE"],
                column_names=["value"],
                return_format="CALCULATION",
                return_size=10,
                include_bounds=False,
                exclude_observations=False,
            )
            if last_rows and last_rows[0].get("Maximum") is not None:
                if float(last_rows[0]["Maximum"]) == pytest.approx(expected_value):
                    return last_rows
                last_error = "expected %r, got %r" % (expected_value, last_rows[0].get("Maximum"))
            else:
                last_error = "no value returned"
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Historian queryAggregatedPoints did not return expected row: path=%r last_rows=%r last_error=%s"
        % (history_path, last_rows, last_error)
    )


def eventually_assert_annotation_deleted(fx, history_path, start_time, end_time, storage_id):
    deadline = time.monotonic() + float(os.getenv("FLUXY_HISTORIAN_TIMEOUT_SECONDS", "20"))
    last_annotations = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_annotations = fx.historian.query_annotations(
                [history_path], start_time, end_date=end_time, allowed_types=["note"]
            )
            if all(annotation.storage_id != storage_id for annotation in last_annotations):
                return
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Historian deleteAnnotations did not remove annotation: path=%r storage_id=%r last_annotations=%r last_error=%s"
        % (history_path, storage_id, last_annotations, last_error)
    )


def eventually_query_metadata(fx, history_path, start_time, end_time, marker):
    deadline = time.monotonic() + float(os.getenv("FLUXY_HISTORIAN_TIMEOUT_SECONDS", "20"))
    last_metadata = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_metadata = fx.historian.query_metadata(
                [history_path], start_date=start_time, end_date=end_time
            )
            for metadata in last_metadata:
                if metadata.properties and metadata.properties.get("documentation") == marker:
                    return metadata
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Historian queryMetadata did not return stored metadata: path=%r marker=%r last_metadata=%r last_error=%s"
        % (history_path, marker, last_metadata, last_error)
    )


def eventually_query_exact_window(fx, history_path, timestamp, expected_value):
    deadline = time.monotonic() + float(os.getenv("FLUXY_HISTORIAN_TIMEOUT_SECONDS", "20"))
    last_rows = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_rows = fx.historian.query_raw_points(
                [history_path], timestamp - 86_400_000, timestamp + 86_400_000, return_size=100
            )
            for row in last_rows:
                if "value" in row and float(row["value"]) == expected_value:
                    return row
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Historian query did not return backfilled point: path=%r timestamp=%r expected=%r last_rows=%r last_error=%s"
        % (history_path, timestamp, expected_value, last_rows, last_error)
    )


def eventually_query_history_value(fx, history_path, timestamp, expected_value):
    deadline = time.monotonic() + float(os.getenv("FLUXY_HISTORIAN_TIMEOUT_SECONDS", "20"))
    last_rows = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_rows = fx.historian.query_raw_points(
                [history_path], timestamp - 5_000, timestamp + 5_000, return_size=10
            )
            for row in last_rows:
                if "value" in row and float(row["value"]) == pytest.approx(expected_value):
                    return row
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Historian datatype boundary query failed: path=%r timestamp=%r expected=%r last_rows=%r last_error=%s"
        % (history_path, timestamp, expected_value, last_rows, last_error)
    )


def query_rows_for_short_boundary_window(fx, history_path, timestamp):
    deadline = time.monotonic() + float(os.getenv("FLUXY_HISTORIAN_BOUNDARY_TIMEOUT_SECONDS", "5"))
    last_rows = []
    while time.monotonic() < deadline:
        last_rows = fx.historian.query_raw_points(
            [history_path], timestamp - 5_000, timestamp + 5_000, return_size=10
        )
        if last_rows:
            return last_rows
        time.sleep(0.5)
    return last_rows


def millis_utc(year, month, day, hour, minute, second):
    value = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)
