import os

import pytest

import fluxy
from fluxy import FluxyError

from path_helpers import join_tag_path


@pytest.mark.integration
def test_move_and_rename_cycles_preserve_new_location_and_remove_old_location():
    base_url = os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux")
    token = os.getenv("FLUXY_TOKEN")
    timeout_ms = int(os.getenv("FLUXY_TIMEOUT_MS", "45000"))
    provider_path = os.getenv("FLUXY_CONFIGURE_BASE_PATH", "[default]")
    root_folder = os.getenv("FLUXY_MOVE_RENAME_FOLDER", "FluxyMoveRenameIntegration")
    base_path = provider_path.rstrip("/")
    root_path = join_tag_path(base_path, root_folder)

    move_source_path = join_tag_path(root_path, "MoveSource", "MoveOriginalTag")
    move_destination_folder = join_tag_path(root_path, "MoveDestination")
    move_destination_path = join_tag_path(move_destination_folder, "MoveOriginalTag")
    rename_old_path = join_tag_path(root_path, "RenameFolder", "RenameOriginalTag")
    rename_new_path = join_tag_path(root_path, "RenameFolder", "RenameNewTag")

    fx = fluxy.Fluxy(base_url=base_url, token=token)

    try:
        fx.tag.configure([tag_tree(root_folder)], base_path=base_path, collision_policy="o")

        move_initial = fx.tag.read_blocking(move_source_path, timeout=timeout_ms)
        move_result = fx.tag.move(move_source_path, move_destination_folder)
        move_old = fx.tag.read_blocking(move_source_path, timeout=timeout_ms)
        move_new = fx.tag.read_blocking(move_destination_path, timeout=timeout_ms)

        rename_initial = fx.tag.read_blocking(rename_old_path, timeout=timeout_ms)
        rename_result = fx.tag.rename(rename_old_path, "RenameNewTag")
        rename_old = fx.tag.read_blocking(rename_old_path, timeout=timeout_ms)
        rename_new = fx.tag.read_blocking(rename_new_path, timeout=timeout_ms)
    except FluxyError as exc:
        pytest.fail(
            "Fluxy move/rename integration failed: %s\nbase_url=%s\nbase_path=%s\nroot_path=%s"
            % (exc, base_url, base_path, root_path)
        )
    finally:
        try:
            fx.tag.delete_tags([root_path])
        except FluxyError:
            pass

    assert move_initial.quality.startswith("Good"), move_initial
    assert move_initial.value == "move-sentinel"
    assert move_result.quality.startswith("Good"), move_result
    assert not move_old.quality.startswith("Good"), move_old
    assert move_new.quality.startswith("Good"), move_new
    assert move_new.value == "move-sentinel"

    assert rename_initial.quality.startswith("Good"), rename_initial
    assert rename_initial.value == 314
    assert rename_result.quality.startswith("Good"), rename_result
    assert not rename_old.quality.startswith("Good"), rename_old
    assert rename_new.quality.startswith("Good"), rename_new
    assert rename_new.value == 314


def tag_tree(root_folder):
    return {
        "name": root_folder,
        "tagType": "Folder",
        "tags": [
            {
                "name": "MoveSource",
                "tagType": "Folder",
                "tags": [
                    {
                        "name": "MoveOriginalTag",
                        "tagType": "AtomicTag",
                        "valueSource": "memory",
                        "dataType": "String",
                        "value": "move-sentinel",
                    }
                ],
            },
            {"name": "MoveDestination", "tagType": "Folder"},
            {
                "name": "RenameFolder",
                "tagType": "Folder",
                "tags": [
                    {
                        "name": "RenameOriginalTag",
                        "tagType": "AtomicTag",
                        "valueSource": "memory",
                        "dataType": "Int4",
                        "value": 314,
                    }
                ],
            },
        ],
    }
