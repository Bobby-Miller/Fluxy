import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


pytestmark = pytest.mark.integration

DEFAULT_SQL_HISTORIAN_PREFIX = (
    "histprov:postgresHist:/sys:gateway:/prov:default:/tag:FluxySqlHistorianIntegration"
)


def test_store_and_query_sql_historian_points_closed_loop():
    fx = fluxy_client()
    path_prefix = sql_historian_prefix()
    history_path = path_prefix + "/" + uuid4().hex
    base_millis = int(time.time() * 1000) - 60_000
    values = [12.5, 13.5, 14.5]
    timestamps = [base_millis, base_millis + 1_000, base_millis + 2_000]

    try:
        prepare_gateway(fx)
        qualities = fx.historian.store_data_points(
            [history_path, history_path, history_path],
            values,
            timestamps=timestamps,
            qualities=[192, 192, 192],
        )
        rows = eventually_query_sql_aggregate(
            fx,
            history_path,
            start_time=base_millis - 5_000,
            end_time=base_millis + 10_000,
            aggregates=["Count", "Minimum", "Maximum"],
            expected={"Count": 3.0, "Minimum": 12.5, "Maximum": 14.5},
        )
        browse_results = eventually_browse_sql_path(fx, path_prefix, history_path)
    except FluxyError as exc:
        pytest.fail("Fluxy SQL historian integration failed: %s\nhistory_path=%s" % (exc, history_path))

    assert all(quality.startswith("Good") for quality in qualities), qualities
    assert any(same_historical_tag(result.path, history_path) for result in browse_results)
    assert float(rows[0]["Count"]) == pytest.approx(3.0)
    assert float(rows[0]["Maximum"]) == pytest.approx(14.5)


def test_store_and_query_sql_historian_backfilled_points_for_2024_and_2025():
    fx = fluxy_client()
    path_prefix = sql_historian_prefix()
    history_path = path_prefix + "/Backfill/" + uuid4().hex
    samples = [
        (millis_utc(2024, 2, 3, 4, 5, 6), 24.203),
        (millis_utc(2024, 11, 12, 13, 14, 15), 24.912),
        (millis_utc(2025, 1, 7, 8, 9, 10), 25.107),
        (millis_utc(2025, 10, 21, 22, 23, 24), 25.821),
    ]

    try:
        prepare_gateway(fx)
        qualities = fx.historian.store_data_points(
            [history_path for _sample in samples],
            [sample[1] for sample in samples],
            timestamps=[sample[0] for sample in samples],
            qualities=[192 for _sample in samples],
        )
        rows_by_timestamp = {
            timestamp: eventually_query_sql_last_value(fx, history_path, timestamp, value)
            for timestamp, value in samples
        }
    except FluxyError as exc:
        pytest.fail("Fluxy SQL historian backfill integration failed: %s\nhistory_path=%s" % (exc, history_path))

    assert all(quality.startswith("Good") for quality in qualities), qualities
    assert set(rows_by_timestamp) == {sample[0] for sample in samples}


def test_query_aggregated_sql_historian_points_closed_loop():
    fx = fluxy_client()
    history_path = sql_historian_prefix() + "/Aggregated/" + uuid4().hex
    base_millis = int(time.time() * 1000) - 60_000
    timestamps = [base_millis, base_millis + 10_000, base_millis + 20_000]

    try:
        prepare_gateway(fx)
        qualities = fx.historian.store_data_points(
            [history_path, history_path, history_path],
            [10.0, 20.0, 30.0],
            timestamps=timestamps,
            qualities=[192, 192, 192],
        )
        rows = eventually_query_sql_aggregate(
            fx,
            history_path,
            start_time=base_millis - 10_000,
            end_time=base_millis + 30_000,
            aggregates=["Maximum"],
            expected={"Maximum": 30.0},
        )
    except FluxyError as exc:
        pytest.fail("Fluxy SQL historian aggregated integration failed: %s\nhistory_path=%s" % (exc, history_path))

    assert all(quality.startswith("Good") for quality in qualities), qualities
    assert rows
    assert float(rows[0]["Maximum"]) == pytest.approx(30.0)


def test_configured_tag_values_define_sql_historian_datatype_boundaries():
    fx = fluxy_client()
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    root_folder = "FluxySqlHistorianTypeBoundary_%s" % uuid4().hex
    root_path = join_tag_path(provider_path.rstrip("/"), root_folder)
    history_prefix = sql_historian_prefix() + "/TypeBoundary/" + uuid4().hex
    timestamp = int(time.time() * 1000) - 60_000
    supported_cases = [
        ("BooleanTag", "Boolean", True, 1.0),
        ("Int4Tag", "Int4", 7, 7.0),
        ("Int8Tag", "Int8", 1234567890123, 1234567890123.0),
        ("Float8Tag", "Float8", 7.75, 7.75),
        ("DateTimeTag", "DateTime", 1778545000000, 1778545000000.0),
        ("StringTag", "String", "hello-sql-history", "hello-sql-history"),
    ]
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
    tag_configs.append(
        {
            "name": document_case[0],
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": document_case[1],
            "value": document_case[2],
        }
    )
    tag_paths = [join_tag_path(root_path, config["name"]) for config in tag_configs]

    try:
        prepare_gateway(fx)
        configure_results = fx.tag.configure(
            [{"name": root_folder, "tagType": "Folder", "tags": tag_configs}],
            base_path=provider_path.rstrip("/"),
            collision_policy="o",
        )
        read_values = fx.tag.read_blocking(tag_paths, timeout_ms=timeout_ms)
        stored_rows = {}
        qualities = []
        for index, (_name, data_type, _tag_value, expected_history_value) in enumerate(supported_cases):
            history_path = history_prefix + "/" + data_type
            qualities.extend(
                fx.historian.store_data_points(
                    [history_path], [read_values[index].value], timestamps=[timestamp + index], qualities=[192]
                )
            )
            stored_rows[data_type] = eventually_query_sql_last_value(
                fx, history_path, timestamp + index, expected_history_value
            )

        document_index = len(supported_cases)
        with pytest.raises(FluxyError):
            fx.historian.store_data_points(
                [history_prefix + "/Document"],
                [read_values[document_index].value],
                timestamps=[timestamp + document_index],
                qualities=[192],
            )
    except FluxyError as exc:
        pytest.fail("Fluxy SQL historian datatype boundary integration failed: %s" % exc)
    finally:
        try:
            fx.tag.delete_tags([root_path])
        except FluxyError:
            pass

    assert all(result.quality.startswith("Good") for result in configure_results), configure_results
    assert all(value.quality.startswith("Good") for value in read_values), read_values
    assert all(quality.startswith("Good") for quality in qualities), qualities
    assert set(stored_rows) == {case[1] for case in supported_cases}


def fluxy_client():
    return fluxy.Fluxy(
        base_url=os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux"),
        token=os.getenv("FLUXY_TOKEN"),
        project_location=os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project"),
    )


def prepare_gateway(fx):
    fx.deploy_webdev()
    fx.project.request_scan()


def sql_historian_prefix():
    return os.getenv("FLUXY_SQL_HISTORIAN_TEST_PATH_PREFIX", DEFAULT_SQL_HISTORIAN_PREFIX).rstrip("/")


def eventually_query_sql_last_value(fx, history_path, timestamp, expected_value):
    return eventually_query_sql_aggregate(
        fx,
        history_path,
        start_time=timestamp - 86_400_000,
        end_time=timestamp + 86_400_000,
        aggregates=["LastValue"],
        expected={"LastValue": expected_value},
    )[0]


def eventually_query_sql_aggregate(fx, history_path, start_time, end_time, aggregates, expected):
    if len(aggregates) > 1:
        rows_by_aggregate = [
            eventually_query_sql_aggregate(
                fx,
                history_path,
                start_time,
                end_time,
                [aggregate],
                {aggregate: expected[aggregate]},
            )[0]
            for aggregate in aggregates
        ]
        merged_row = {}
        for row in rows_by_aggregate:
            merged_row.update(row)
        return [merged_row]

    deadline = time.monotonic() + float(os.getenv("FLUXY_SQL_HISTORIAN_TIMEOUT_SECONDS", "30"))
    last_rows = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_rows = fx.historian.query_aggregated_points(
                [history_path],
                start_time,
                end_time,
                aggregates=aggregates,
                fill_modes=["NONE" for _aggregate in aggregates],
                column_names=["value"],
                return_format="CALCULATION",
                return_size=10,
                include_bounds=False,
                exclude_observations=False,
            )
            if last_rows and aggregate_row_matches(last_rows[0], expected):
                return last_rows
            last_error = "expected %r, got %r" % (expected, last_rows[0] if last_rows else None)
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "SQL historian aggregate query did not return expected row: path=%r last_rows=%r last_error=%s"
        % (history_path, last_rows, last_error)
    )


def aggregate_row_matches(row, expected):
    for key, expected_value in expected.items():
        value = row.get(key)
        if value is None:
            return False
        if isinstance(expected_value, str):
            if value != expected_value:
                return False
        elif float(value) != pytest.approx(expected_value):
            return False
    return True


def eventually_browse_sql_path(fx, browse_path, expected_path):
    deadline = time.monotonic() + float(os.getenv("FLUXY_SQL_HISTORIAN_TIMEOUT_SECONDS", "30"))
    last_results = []
    last_error = None
    while time.monotonic() < deadline:
        try:
            last_results = fx.historian.browse(browse_path)
            if any(same_historical_tag(result.path, expected_path) for result in last_results):
                return last_results
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "SQL historian browse did not return stored path: browse_path=%r expected=%r last_results=%r last_error=%s"
        % (browse_path, expected_path, last_results, last_error)
    )


def same_historical_tag(actual_path, expected_path):
    return historical_tag_suffix(actual_path) == historical_tag_suffix(expected_path)


def historical_tag_suffix(path):
    marker = ":/tag:"
    marker_index = path.find(marker)
    if marker_index < 0:
        return path
    return path[marker_index + len(marker) :]


def millis_utc(year, month, day, hour, minute, second):
    value = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)
