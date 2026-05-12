import json
import math
import os
from pathlib import Path

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tags" / "fluxy_import_export_source.json"
EXPECTED_VALUES = ["fluxy-import-export-sentinel-string", False, 1, 1.5]
EXPECTED_TAG_NAMES = [
    "FluxyImportExportSentinel_String_91B7",
    "FluxyImportExportSentinel_Boolean_42C9",
    "FluxyImportExportSentinel_Integer_73D1",
    "FluxyImportExportSentinel_Float_28A6",
]


@pytest.mark.integration
def test_imports_reads_exports_confirms_configuration_and_deletes_tags():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]")
    folder_name = os.getenv("FLUXY_IMPORT_EXPORT_FOLDER", "FluxyImportExportSentinelFolder_5F3A")
    base_path = provider_path.rstrip("/")

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fixture["name"] = folder_name
    assert [tag["name"] for tag in fixture["tags"]] == EXPECTED_TAG_NAMES
    tag_paths = [join_tag_path(base_path, folder_name, tag["name"]) for tag in fixture["tags"]]
    folder_path = join_tag_path(base_path, folder_name)

    fx = fluxy.Fluxy(base_url=base_url, token=token)

    try:
        import_results = fx.tag.import_tags(fixture, base_path=base_path, collision_policy="o")
        read_values = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
        export_result = fx.tag.export_tags(folder_path)
        delete_results = fx.tag.delete_tags([folder_path])
        post_delete_values = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
    except FluxyError as exc:
        pytest.fail(
            "Fluxy import/export integration failed: %s\nbase_url=%s\nbase_path=%s\nfolder_name=%s\ntag_paths=%r"
            % (exc, base_url, base_path, folder_name, tag_paths)
        )
    finally:
        try:
            fx.tag.delete_tags([folder_path])
        except FluxyError:
            pass

    bad_imports = [result for result in import_results if not result.quality.startswith("Good")]
    assert not bad_imports, "Import returned bad qualities: %r" % bad_imports

    assert_values_match(read_values, EXPECTED_VALUES)

    exported = export_result.tags
    assert exported["name"] == folder_name
    assert exported["tagType"] == "Folder"
    assert_tag_configs_match(exported["tags"], fixture["tags"])

    bad_deletes = [result for result in delete_results if not result.quality.startswith("Good")]
    assert not bad_deletes, "Delete returned bad qualities: %r" % bad_deletes
    assert not [value for value in post_delete_values if value.quality.startswith("Good")]


def assert_tag_configs_match(exported_tags, expected_tags):
    exported_by_name = {tag["name"]: tag for tag in exported_tags}
    for expected in expected_tags:
        exported = exported_by_name[expected["name"]]
        assert exported["tagType"] == expected["tagType"]
        assert exported["valueSource"] == expected["valueSource"]
        assert exported["dataType"] == expected["dataType"]
        assert exported["value"] == expected["value"]


def assert_values_match(actual_values, expected_values):
    assert len(actual_values) == len(expected_values)
    for actual, expected in zip(actual_values, expected_values, strict=True):
        assert actual.quality.startswith("Good"), actual
        if isinstance(expected, float):
            assert math.isclose(float(actual.value), expected, rel_tol=0.0, abs_tol=0.0001)
        else:
            assert actual.value == expected
