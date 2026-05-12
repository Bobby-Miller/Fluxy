import math
import os
import time
from uuid import uuid4

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


INITIAL_VALUES = ["hello", False, 0, 1.0]
UPDATED_VALUES = ["world", True, 1, 6.7]

STRESS_INITIAL_VALUES = ["alpha", False, 123, 4.5, 1234567890123, {"nested": {"n": 1}, "items": [1, "two"]}]
STRESS_UPDATED_VALUES = ["omega", True, 456, 9.25, 9876543210123, {"nested": {"n": 2}, "items": [3, "four"]}]
STRESS_OVERWRITE_VALUES = ["omega", True, 789, 9.25, 9876543210123, {"nested": {"n": 2}, "items": [3, "four"]}]


def _tag_configs():
    return [
        {
            "name": "StringTag",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "String",
            "value": INITIAL_VALUES[0],
        },
        {
            "name": "BooleanTag",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Boolean",
            "value": INITIAL_VALUES[1],
        },
        {
            "name": "IntegerTag",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Int4",
            "value": INITIAL_VALUES[2],
        },
        {
            "name": "FloatTag",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Float4",
            "value": INITIAL_VALUES[3],
        },
    ]


def _assert_values_match(actual_values, expected_values):
    assert len(actual_values) == len(expected_values)
    for actual, expected in zip(actual_values, expected_values, strict=True):
        assert actual.quality.startswith("Good"), actual
        if isinstance(expected, float):
            assert math.isclose(float(actual.value), expected, rel_tol=0.0, abs_tol=0.0001)
        else:
            assert actual.value == expected


def _stress_tag_configs():
    names_and_types = [
        ("StringMix", "String", STRESS_INITIAL_VALUES[0]),
        ("BooleanMix", "Boolean", STRESS_INITIAL_VALUES[1]),
        ("Int4Mix", "Int4", STRESS_INITIAL_VALUES[2]),
        ("Float4Mix", "Float4", STRESS_INITIAL_VALUES[3]),
        ("Int8Mix", "Int8", STRESS_INITIAL_VALUES[4]),
        ("DocumentMix", "Document", STRESS_INITIAL_VALUES[5]),
    ]
    return [
        {
            "name": name,
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": data_type,
            "value": value,
            "documentation": "initial-%s" % name,
        }
        for name, data_type, value in names_and_types
    ]


def _assert_good_results(results, operation):
    bad_results = [result for result in results if not result.quality.startswith("Good")]
    assert not bad_results, "%s returned bad qualities: %r" % (operation, bad_results)


@pytest.mark.integration
def test_configures_reads_writes_and_reads_back_basic_memory_types():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]")
    folder_name = os.getenv("FLUXY_CONFIGURE_FOLDER", "FluxyIntegration")
    base_path = provider_path.rstrip("/")

    tag_configs = _tag_configs()
    folder_config = {"name": folder_name, "tagType": "Folder", "tags": tag_configs}
    tag_paths = [join_tag_path(base_path, folder_name, tag["name"]) for tag in tag_configs]

    fx = fluxy.Fluxy(base_url=base_url, token=token)

    try:
        configure_results = fx.tag.configure([folder_config], base_path=base_path, collision_policy="o")
        configured_values = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
        write_results = fx.tag.write_blocking(tag_paths, UPDATED_VALUES, timeout=timeout_ms)
        readback_values = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
    except FluxyError as exc:
        pytest.fail(
            "Fluxy configure/write/readback failed: %s\nbase_url=%s\nbase_path=%s\n"
            "folder_name=%s\ntag_paths=%r"
            % (exc, base_url, base_path, folder_name, tag_paths)
        )
    finally:
        try:
            fx.tag.delete_tags([join_tag_path(base_path, folder_name)])
        except FluxyError:
            pass

    bad_configures = [result for result in configure_results if not result.quality.startswith("Good")]
    assert not bad_configures, "Configure returned bad qualities: %r" % bad_configures

    _assert_values_match(configured_values, INITIAL_VALUES)

    bad_writes = [result for result in write_results if not result.quality.startswith("Good")]
    assert not bad_writes, "Write returned bad qualities: %r" % bad_writes

    _assert_values_match(readback_values, UPDATED_VALUES)


@pytest.mark.integration
def test_configure_write_move_rename_and_merge_mixed_memory_types():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]")
    root_folder = "FluxyTagStress_%s" % uuid4().hex
    base_path = provider_path.rstrip("/")
    root_path = join_tag_path(base_path, root_folder)
    source_folder = join_tag_path(root_path, "Source")
    destination_folder = join_tag_path(root_path, "Destination")
    moved_folder = join_tag_path(destination_folder, "Source")
    renamed_folder = join_tag_path(destination_folder, "RenamedSource")
    tag_names = [config["name"] for config in _stress_tag_configs()]
    source_paths = [join_tag_path(source_folder, name) for name in tag_names]
    renamed_paths = [join_tag_path(renamed_folder, name) for name in tag_names]
    added_path = join_tag_path(renamed_folder, "AddedByMerge")

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        configure_results = fx.tag.configure(
            [
                {
                    "name": root_folder,
                    "tagType": "Folder",
                    "tags": [
                        {"name": "Source", "tagType": "Folder", "tags": _stress_tag_configs()},
                        {"name": "Destination", "tagType": "Folder"},
                    ],
                }
            ],
            base_path=base_path,
            collision_policy="o",
        )
        initial_values = eventually_read_good(fx, source_paths, STRESS_INITIAL_VALUES, timeout_ms)
        write_results = fx.tag.write_blocking(source_paths, STRESS_UPDATED_VALUES, timeout=timeout_ms)
        written_values = eventually_read_good(fx, source_paths, STRESS_UPDATED_VALUES, timeout_ms)
        move_result = fx.tag.move(source_folder, destination_folder)
        moved_values = eventually_read_good(fx, [join_tag_path(moved_folder, name) for name in tag_names], STRESS_UPDATED_VALUES, timeout_ms)
        rename_result = fx.tag.rename(moved_folder, "RenamedSource")
        renamed_values = eventually_read_good(fx, renamed_paths, STRESS_UPDATED_VALUES, timeout_ms)
        merge_results = fx.tag.configure(
            [
                {
                    "name": "StringMix",
                    "tagType": "AtomicTag",
                    "valueSource": "memory",
                    "dataType": "String",
                    "documentation": "merged-string-doc",
                    "tooltip": "merged-string-tooltip",
                },
                {
                    "name": "AddedByMerge",
                    "tagType": "AtomicTag",
                    "valueSource": "memory",
                    "dataType": "String",
                    "value": "added",
                    "documentation": "added-by-merge-doc",
                },
            ],
            base_path=renamed_folder,
            collision_policy="m",
        )
        after_merge_values = eventually_read_good(fx, [*renamed_paths, added_path], [*STRESS_UPDATED_VALUES, "added"], timeout_ms)
        overwrite_results = fx.tag.configure(
            [
                {
                    "name": "Int4Mix",
                    "tagType": "AtomicTag",
                    "valueSource": "memory",
                    "dataType": "Int4",
                    "value": STRESS_OVERWRITE_VALUES[2],
                    "documentation": "overwritten-int-doc",
                }
            ],
            base_path=renamed_folder,
            collision_policy="o",
        )
        after_overwrite_values = eventually_read_good(
            fx, [*renamed_paths, added_path], [*STRESS_OVERWRITE_VALUES, "added"], timeout_ms
        )
        renamed_config = fx.tag.get_configuration(renamed_folder, recursive=True)
        old_source_read = fx.tag.read_blocking(source_folder, timeout=timeout_ms)
        moved_source_read = fx.tag.read_blocking(moved_folder, timeout=timeout_ms)
    except FluxyError as exc:
        pytest.fail(
            "Fluxy tag stress integration failed: %s\nbase_url=%s\nroot_path=%s"
            % (exc, base_url, root_path)
        )
    finally:
        try:
            fx.tag.delete_tags([root_path])
        except FluxyError:
            pass

    _assert_good_results(configure_results, "configure")
    _assert_values_match(initial_values, STRESS_INITIAL_VALUES)
    _assert_good_results(write_results, "writeBlocking")
    _assert_values_match(written_values, STRESS_UPDATED_VALUES)
    assert move_result.quality.startswith("Good"), move_result
    _assert_values_match(moved_values, STRESS_UPDATED_VALUES)
    assert rename_result.quality.startswith("Good"), rename_result
    _assert_values_match(renamed_values, STRESS_UPDATED_VALUES)
    _assert_good_results(merge_results, "configure merge")
    _assert_values_match(after_merge_values, [*STRESS_UPDATED_VALUES, "added"])
    _assert_good_results(overwrite_results, "configure overwrite")
    _assert_values_match(after_overwrite_values, [*STRESS_OVERWRITE_VALUES, "added"])
    assert not old_source_read.quality.startswith("Good"), old_source_read
    assert not moved_source_read.quality.startswith("Good"), moved_source_read

    assert len(renamed_config) == 1
    recursive_root = renamed_config[0]
    assert recursive_root["name"] == "RenamedSource"
    child_configs = {child["name"]: child for child in recursive_root.get("tags", [])}
    assert set(child_configs) == {*tag_names, "AddedByMerge"}
    assert child_configs["StringMix"]["documentation"] == "merged-string-doc"
    assert child_configs["StringMix"]["tooltip"] == "merged-string-tooltip"
    assert child_configs["Int4Mix"]["documentation"] == "overwritten-int-doc"
    assert child_configs["AddedByMerge"]["documentation"] == "added-by-merge-doc"


@pytest.mark.integration
def test_configure_collision_policies_with_special_names_and_type_change():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]")
    root_folder = "FluxyCollision_%s" % uuid4().hex
    base_path = provider_path.rstrip("/")
    root_path = join_tag_path(base_path, root_folder)
    tag_name = "Tag With Spaces-And_Dashes"
    tag_path = join_tag_path(root_path, tag_name)

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        initial_results = fx.tag.configure(
            [
                {
                    "name": root_folder,
                    "tagType": "Folder",
                    "tags": [
                        {
                            "name": tag_name,
                            "tagType": "AtomicTag",
                            "valueSource": "memory",
                            "dataType": "String",
                            "value": "original",
                            "documentation": "original-doc",
                        }
                    ],
                }
            ],
            base_path=base_path,
            collision_policy="o",
        )
        ignored_results = fx.tag.configure(
            [
                {
                    "name": tag_name,
                    "tagType": "AtomicTag",
                    "valueSource": "memory",
                    "dataType": "String",
                    "value": "ignored",
                    "documentation": "ignored-doc",
                }
            ],
            base_path=root_path,
            collision_policy="i",
        )
        ignored_value = eventually_read_good(fx, [tag_path], ["original"], timeout_ms)[0]
        merge_results = fx.tag.configure(
            [
                {
                    "name": tag_name,
                    "tagType": "AtomicTag",
                    "valueSource": "memory",
                    "dataType": "String",
                    "documentation": "merged-doc",
                    "tooltip": "merged-tooltip",
                }
            ],
            base_path=root_path,
            collision_policy="m",
        )
        merged_value = eventually_read_good(fx, [tag_path], ["original"], timeout_ms)[0]
        merged_config = fx.tag.get_configuration(tag_path)[0]
        overwrite_results = fx.tag.configure(
            [
                {
                    "name": tag_name,
                    "tagType": "AtomicTag",
                    "valueSource": "memory",
                    "dataType": "Int4",
                    "value": 99,
                    "documentation": "overwritten-doc",
                }
            ],
            base_path=root_path,
            collision_policy="o",
        )
        overwritten_value = eventually_read_good(fx, [tag_path], [99], timeout_ms)[0]
        overwritten_config = fx.tag.get_configuration(tag_path)[0]
    except FluxyError as exc:
        pytest.fail("Fluxy collision policy stress failed: %s\nroot_path=%s" % (exc, root_path))
    finally:
        try:
            fx.tag.delete_tags([root_path])
        except FluxyError:
            pass

    _assert_good_results(initial_results, "initial configure")
    _assert_good_results(ignored_results, "ignore configure")
    assert ignored_value.value == "original"
    _assert_good_results(merge_results, "merge configure")
    assert merged_value.value == "original"
    assert merged_config["documentation"] == "merged-doc"
    assert merged_config["tooltip"] == "merged-tooltip"
    _assert_good_results(overwrite_results, "overwrite configure")
    assert overwritten_value.value == 99
    assert overwritten_config["dataType"] == "Int4"
    assert overwritten_config["documentation"] == "overwritten-doc"


@pytest.mark.integration
def test_copy_export_import_round_trips_document_and_datetime_tags():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]")
    root_folder = "FluxyRoundTrip_%s" % uuid4().hex
    base_path = provider_path.rstrip("/")
    root_path = join_tag_path(base_path, root_folder)
    source_folder = join_tag_path(root_path, "Source")
    copied_folder = join_tag_path(root_path, "Copied")
    imported_folder_name = "Imported"
    imported_folder = join_tag_path(root_path, imported_folder_name)
    document_value = {"alpha": 1, "nested": {"enabled": True}, "items": ["a", 2]}
    datetime_value = 1_778_545_000_000
    source_paths = [join_tag_path(source_folder, "DocumentTag"), join_tag_path(source_folder, "DateTimeTag")]
    copied_paths = [join_tag_path(copied_folder, "DocumentTag"), join_tag_path(copied_folder, "DateTimeTag")]
    imported_paths = [join_tag_path(imported_folder, "DocumentTag"), join_tag_path(imported_folder, "DateTimeTag")]
    expected_values = [document_value, datetime_value]

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        configure_results = fx.tag.configure(
            [
                {
                    "name": root_folder,
                    "tagType": "Folder",
                    "tags": [
                        {
                            "name": "Source",
                            "tagType": "Folder",
                            "tags": [
                                {
                                    "name": "DocumentTag",
                                    "tagType": "AtomicTag",
                                    "valueSource": "memory",
                                    "dataType": "Document",
                                    "value": document_value,
                                },
                                {
                                    "name": "DateTimeTag",
                                    "tagType": "AtomicTag",
                                    "valueSource": "memory",
                                    "dataType": "DateTime",
                                    "value": datetime_value,
                                },
                            ],
                        },
                        {"name": "Copied", "tagType": "Folder"},
                    ],
                }
            ],
            base_path=base_path,
            collision_policy="o",
        )
        source_values = eventually_read_good(fx, source_paths, expected_values, timeout_ms)
        copy_result = fx.tag.copy(source_paths, copied_folder)
        copied_values = eventually_read_good(fx, copied_paths, expected_values, timeout_ms)
        export_result = fx.tag.export_tags(source_folder)
        imported_tags = export_result.tags
        imported_tags["name"] = imported_folder_name
        import_results = fx.tag.import_tags(imported_tags, base_path=root_path, collision_policy="o")
        imported_values = eventually_read_good(fx, imported_paths, expected_values, timeout_ms)
        imported_config = fx.tag.get_configuration(imported_folder, recursive=True)[0]
    except FluxyError as exc:
        pytest.fail("Fluxy complex round-trip stress failed: %s\nroot_path=%s" % (exc, root_path))
    finally:
        try:
            fx.tag.delete_tags([root_path])
        except FluxyError:
            pass

    _assert_good_results(configure_results, "configure")
    _assert_values_match(source_values, expected_values)
    _assert_good_results(copy_result, "copy")
    _assert_values_match(copied_values, expected_values)
    _assert_good_results(import_results, "import")
    _assert_values_match(imported_values, expected_values)
    imported_by_name = {child["name"]: child for child in imported_config.get("tags", [])}
    assert imported_by_name["DocumentTag"]["dataType"] == "Document"
    assert imported_by_name["DocumentTag"]["value"] == document_value
    assert imported_by_name["DateTimeTag"]["dataType"] == "DateTime"


def eventually_read_good(fx, paths, expected_values, timeout_ms):
    deadline = time.monotonic() + float(os.getenv("FLUXY_TAG_STRESS_TIMEOUT_SECONDS", "20"))
    last_values = []
    while time.monotonic() < deadline:
        values = fx.tag.read_blocking(paths, timeout=timeout_ms)
        last_values = values if isinstance(values, list) else [values]
        if len(last_values) == len(expected_values) and all(
            value.quality.startswith("Good") for value in last_values
        ):
            try:
                _assert_values_match(last_values, expected_values)
                return last_values
            except AssertionError:
                pass
        time.sleep(0.5)
    pytest.fail("Expected good tag values %r at %r, got %r" % (expected_values, paths, last_values))
