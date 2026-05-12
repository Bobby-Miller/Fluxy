import math
import os

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path

WRITE_VALUES = [1.1, 2.2, 3.3, 4.4, 5.5]


@pytest.mark.integration
def test_writes_generated_memory_tags_and_reads_values_back():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]").rstrip("/")
    folder_name = os.getenv("FLUXY_GENERATED_WRITE_FOLDER", "FluxyGeneratedWriteIntegration")
    folder_path = join_tag_path(provider_path, folder_name)
    tag_configs = [
        {
            "name": "GeneratedWrite1",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Float4",
            "value": 0.0,
        },
        {
            "name": "GeneratedWrite2",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Float4",
            "value": 0.0,
        },
        {
            "name": "GeneratedWrite3",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Float4",
            "value": 0.0,
        },
        {
            "name": "GeneratedWrite4",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Float4",
            "value": 0.0,
        },
        {
            "name": "GeneratedWrite5",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Float4",
            "value": 0.0,
        },
    ]
    tag_paths = [join_tag_path(folder_path, tag["name"]) for tag in tag_configs]

    fx = fluxy.Fluxy(base_url=base_url, token=token)
    try:
        fx.tag.configure(
            [{"name": folder_name, "tagType": "Folder", "tags": tag_configs}],
            base_path=provider_path,
            collision_policy="o",
        )
        before = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
        write_results = fx.tag.write_blocking(tag_paths, WRITE_VALUES, timeout=timeout_ms)
        after = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
    except FluxyError as exc:
        pytest.fail(
            "Fluxy write/readback failed: %s\nbase_url=%s\ntoken_configured=%s\n"
            "timeout_ms=%s\ntag_paths=%r\nwrite_values=%r"
            % (exc, base_url, bool(token), timeout_ms, tag_paths, WRITE_VALUES)
        )
    finally:
        try:
            fx.tag.delete_tags([folder_path])
        except FluxyError:
            pass

    bad_before = [value for value in before if not value.quality.startswith("Good")]
    assert not bad_before, "Pre-write read had bad qualities: %r" % bad_before

    bad_writes = [result for result in write_results if not result.quality.startswith("Good")]
    assert not bad_writes, "Write returned bad qualities: %r" % bad_writes

    mismatches = []
    for tag_path, expected, actual in zip(tag_paths, WRITE_VALUES, after, strict=True):
        try:
            actual_float = float(actual.value)
        except (TypeError, ValueError):
            mismatches.append((tag_path, expected, actual.value, actual.quality))
            continue
        if not math.isclose(actual_float, expected, rel_tol=0.0, abs_tol=0.0001):
            mismatches.append((tag_path, expected, actual.value, actual.quality))

    assert not mismatches, "Readback mismatches: %r" % mismatches
