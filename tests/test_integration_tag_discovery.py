import os
import time

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


@pytest.mark.integration
def test_copy_and_query_closed_loop():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    project_location = os.getenv("FLUXY_PROJECT_LOCATION", "../ignition_flux_project")
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]").rstrip("/")
    provider = provider_path.strip("[]")
    root_folder = os.getenv("FLUXY_TAG_DISCOVERY_FOLDER", "FluxyTagDiscoveryIntegration")
    root_path = join_tag_path(provider_path, root_folder)
    source_folder_path = join_tag_path(root_path, "Source")
    destination_folder_path = join_tag_path(root_path, "Destination")
    source_tag_path = join_tag_path(source_folder_path, "CopiedString")
    copied_tag_path = join_tag_path(destination_folder_path, "CopiedString")

    fx = fluxy.Fluxy(base_url=base_url, token=token, project_location=project_location)

    try:
        fx.deploy_webdev()
        fx.project.request_scan()
        fx.tag.configure([tag_tree(root_folder)], base_path=provider_path, collision_policy="o")

        eventually_read_quality(fx, source_tag_path, quality_is_good)
        eventually_read_quality(fx, copied_tag_path, quality_indicates_missing_tag)

        copy_result = fx.tag.copy(source_tag_path, destination_folder_path)
        copied_value = fx.tag.read_blocking(copied_tag_path)
        query_fx = fluxy.Fluxy(base_url=base_url, token=token)
        query_results = eventually_query_contains(
            query_fx,
            provider,
            "CopiedString",
            {
                "condition": {"path": root_folder + "/*", "tagType": "AtomicTag"},
                "returnProperties": ["path", "tagType", "valueSource"],
            },
        )
    except FluxyError as exc:
        pytest.fail("Fluxy tag discovery integration failed: %s\nroot_path=%s" % (exc, root_path))
    finally:
        try:
            fx.tag.delete_tags([root_path])
        except FluxyError:
            pass

    assert copy_result.quality.startswith("Good"), copy_result
    assert copied_value.quality.startswith("Good"), copied_value
    assert copied_value.value == "copy-source"
    assert any("CopiedString" in str(result) for result in query_results), query_results


def tag_tree(root_folder):
    return {
        "name": root_folder,
        "tagType": "Folder",
        "tags": [
            {
                "name": "Source",
                "tagType": "Folder",
                "tags": [
                    {
                        "name": "CopiedString",
                        "tagType": "AtomicTag",
                        "valueSource": "memory",
                        "dataType": "String",
                        "value": "copy-source",
                    }
                ],
            },
            {"name": "Destination", "tagType": "Folder"},
        ],
    }


def eventually_query_contains(fx, provider, expected_text, query):
    deadline = time.monotonic() + float(os.getenv("FLUXY_TAG_QUERY_TIMEOUT_SECONDS", "12"))
    last_error = None
    last_results = []
    while time.monotonic() < deadline:
        try:
            last_results = fx.tag.query(provider, query=query, limit=25)
            if any(expected_text in str(result) for result in last_results):
                return last_results
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Tag query did not return %r: last_results=%r last_error=%s"
        % (expected_text, last_results, last_error)
    )


def eventually_read_quality(fx, tag_path, quality_predicate):
    deadline = time.monotonic() + float(os.getenv("FLUXY_TAG_READ_TIMEOUT_SECONDS", "12"))
    last_error = None
    last_value = None
    while time.monotonic() < deadline:
        try:
            last_value = fx.tag.read_blocking(tag_path)
            if quality_predicate(last_value.quality):
                return last_value
        except FluxyError as exc:
            last_error = exc
        time.sleep(0.5)
    pytest.fail(
        "Tag read did not reach expected quality: tag_path=%r last_value=%r last_error=%s"
        % (tag_path, last_value, last_error)
    )


def quality_is_good(quality):
    return str(quality).startswith("Good")


def quality_indicates_missing_tag(quality):
    normalized = str(quality).replace("_", "").lower()
    return normalized.startswith("bad") and (
        "doesnotexist" in normalized or "notfound" in normalized
    )
