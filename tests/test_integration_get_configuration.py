import os

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


@pytest.mark.integration
def test_configures_gets_configuration_and_deletes_tag():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]")
    folder_name = os.getenv("FLUXY_GET_CONFIGURATION_FOLDER", "FluxyGetConfigurationIntegration")
    tag_name = "ConfiguredTooltipDescriptionTag"
    base_path = provider_path.rstrip("/")
    folder_path = join_tag_path(base_path, folder_name)
    tag_path = join_tag_path(folder_path, tag_name)

    fx = fluxy.Fluxy(base_url=base_url, token=token)

    try:
        configure_results = fx.tag.configure(
            [
                {
                    "name": folder_name,
                    "tagType": "Folder",
                    "tags": [
                        {
                            "name": tag_name,
                            "tagType": "AtomicTag",
                            "valueSource": "memory",
                            "dataType": "String",
                            "value": "configuration-sentinel",
                            "tooltip": "hello Tooltip",
                            "documentation": "Hello Description",
                        }
                    ],
                }
            ],
            base_path=base_path,
            collision_policy="o",
        )
        configs = fx.tag.get_configuration(tag_path)
        delete_results = fx.tag.delete_tags([folder_path])
    except FluxyError as exc:
        pytest.fail(
            "Fluxy getConfiguration integration failed: %s\nbase_url=%s\nbase_path=%s\ntag_path=%s"
            % (exc, base_url, base_path, tag_path)
        )
    finally:
        try:
            fx.tag.delete_tags([folder_path])
        except FluxyError:
            pass

    bad_configures = [result for result in configure_results if not result.quality.startswith("Good")]
    assert not bad_configures, "Configure returned bad qualities: %r" % bad_configures

    assert len(configs) == 1
    config = configs[0]
    assert config["name"] == tag_name
    assert config["tagType"] == "AtomicTag"
    assert config["valueSource"] == "memory"
    assert config["dataType"] == "String"
    assert config["tooltip"] == "hello Tooltip"
    assert config["documentation"] == "Hello Description"

    bad_deletes = [result for result in delete_results if not result.quality.startswith("Good")]
    assert not bad_deletes, "Delete returned bad qualities: %r" % bad_deletes
