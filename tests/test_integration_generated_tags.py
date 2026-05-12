import os

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


@pytest.mark.integration
def test_reads_generated_memory_tags_through_fluxy():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]").rstrip("/")
    folder_name = os.getenv("FLUXY_GENERATED_READ_FOLDER", "FluxyGeneratedReadIntegration")
    folder_path = join_tag_path(provider_path, folder_name)
    tag_configs = [
        {
            "name": "GeneratedString",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "String",
            "value": "generated",
        },
        {
            "name": "GeneratedInteger",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Int4",
            "value": 12,
        },
        {
            "name": "GeneratedFloat",
            "tagType": "AtomicTag",
            "valueSource": "memory",
            "dataType": "Float4",
            "value": 3.4,
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
        values = fx.tag.read_blocking(tag_paths, timeout=timeout_ms)
    except FluxyError as exc:
        pytest.fail(
            "Fluxy read failed: %s\nbase_url=%s\ntoken_configured=%s\ntimeout_ms=%s\ntag_paths=%r"
            % (exc, base_url, bool(token), timeout_ms, tag_paths)
        )
    finally:
        try:
            fx.tag.delete_tags([folder_path])
        except FluxyError:
            pass

    assert len(values) == len(tag_paths), (
        "readBlocking returned %d values for %d paths. sampled_paths=%r returned_values=%r"
        % (len(values), len(tag_paths), tag_paths, values)
    )

    bad_values = []
    for tag_path, value in zip(tag_paths, values, strict=True):
        if not value.quality.startswith("Good"):
            bad_values.append(
                {
                    "tagPath": tag_path,
                    "quality": value.quality,
                    "value": value.value,
                    "timestamp": value.timestamp,
                }
            )

    assert not bad_values, "Bad tag qualities from Fluxy read: %r" % bad_values
