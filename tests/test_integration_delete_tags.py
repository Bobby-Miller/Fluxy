import math
import os

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


@pytest.mark.integration
def test_configures_writes_deletes_and_verifies_tags_are_gone():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]")
    folder_name = os.getenv("FLUXY_DELETE_FOLDER", "FluxyDeleteIntegration")
    base_path = provider_path.rstrip("/")

    initial_values = ["before", False, 1, 1.5]
    updated_values = ["after", True, 2, 2.5]
    tag_configs = [
        {
            "name": "DeleteStringTag",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "String",
            "value": initial_values[0],
        },
        {
            "name": "DeleteBooleanTag",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Boolean",
            "value": initial_values[1],
        },
        {
            "name": "DeleteIntegerTag",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Int4",
            "value": initial_values[2],
        },
        {
            "name": "DeleteFloatTag",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Float4",
            "value": initial_values[3],
        },
    ]
    folder_config = {"name": folder_name, "tagType": "Folder", "tags": tag_configs}
    folder_path = join_tag_path(base_path, folder_name)
    tag_paths = [join_tag_path(folder_path, tag["name"]) for tag in tag_configs]

    fx = fluxy.Fluxy(base_url=base_url, token=token)

    try:
        configure_results = fx.tag.configure([folder_config], base_path=base_path, collision_policy="o")
        configured_values = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
        write_results = fx.tag.write_blocking(tag_paths, updated_values, timeout=timeout_ms)
        readback_values = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
        delete_results = fx.tag.delete_tags([folder_path])
        post_delete_values = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
        browse_results = fx.tag.browse(base_path)
    except FluxyError as exc:
        pytest.fail(
            "Fluxy deleteTags integration failed: %s\nbase_url=%s\nbase_path=%s\nfolder_name=%s\ntag_paths=%r"
            % (exc, base_url, base_path, folder_name, tag_paths)
        )
    finally:
        try:
            fx.tag.delete_tags([folder_path])
        except FluxyError:
            pass

    bad_configures = [result for result in configure_results if not result.quality.startswith("Good")]
    assert not bad_configures, "Configure returned bad qualities: %r" % bad_configures

    assert_values_match(configured_values, initial_values)

    bad_writes = [result for result in write_results if not result.quality.startswith("Good")]
    assert not bad_writes, "Write returned bad qualities: %r" % bad_writes
    assert_values_match(readback_values, updated_values)

    bad_deletes = [result for result in delete_results if not result.quality.startswith("Good")]
    assert not bad_deletes, "Delete returned bad qualities: %r" % bad_deletes

    assert not [value for value in post_delete_values if value.quality.startswith("Good")]
    assert not [result for result in browse_results if result.name == folder_name]


def assert_values_match(actual_values, expected_values):
    assert len(actual_values) == len(expected_values)
    for actual, expected in zip(actual_values, expected_values, strict=True):
        assert actual.quality.startswith("Good"), actual
        if isinstance(expected, float):
            assert math.isclose(float(actual.value), expected, rel_tol=0.0, abs_tol=0.0001)
        else:
            assert actual.value == expected
