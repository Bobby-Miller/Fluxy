import os

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


EXPECTED_TAGS = {"StringTag", "BooleanTag", "IntegerTag", "FloatTag"}


@pytest.mark.integration
def test_browses_configured_memory_type_tags():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]").rstrip("/")
    folder_name = os.getenv("FLUXY_BROWSE_FOLDER", "FluxyBrowseIntegration")
    browse_path = join_tag_path(provider_path, folder_name)

    fx = fluxy.Fluxy(base_url=base_url, token=token)

    try:
        fx.tag.configure([_tag_tree(folder_name)], base_path=provider_path, collision_policy="o")
        results = fx.tag.browse(browse_path)
    except FluxyError as exc:
        pytest.fail("Fluxy browse failed: %s\nbrowse_path=%s" % (exc, browse_path))
    finally:
        try:
            fx.tag.delete_tags([browse_path])
        except FluxyError:
            pass

    names = {result.name for result in results}

    assert EXPECTED_TAGS.issubset(names), "Expected %r in browse names %r" % (EXPECTED_TAGS, names)


def _tag_tree(folder_name):
    return {
        "name": folder_name,
        "tagType": "Folder",
        "tags": [
            {"name": "StringTag", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "String", "value": "hello"},
            {"name": "BooleanTag", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Boolean", "value": False},
            {"name": "IntegerTag", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Int4", "value": 0},
            {"name": "FloatTag", "tagType": "AtomicTag", "valueSource": "memory", "dataType": "Float4", "value": 1.0},
        ],
    }
