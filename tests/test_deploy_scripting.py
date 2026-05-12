import pytest

from fluxy.deploy_scripting import delete_function_file, deploy_builtin_function_file, deploy_function_file


def test_deploy_function_file_writes_ignition_script_resource(tmp_path):
    path = deploy_function_file(tmp_path, "custom_hello.py", "def custom_hello():\n    return 'Hi'\n")

    assert path == tmp_path / "ignition" / "script-python" / "fluxy_functions" / "custom_hello" / "code.py"
    assert path.read_text() == "def custom_hello():\n    return 'Hi'\n"
    assert path.with_name("resource.json").exists()


def test_deploy_builtin_function_file_writes_hello_world(tmp_path):
    path = deploy_builtin_function_file(tmp_path, "hello_world.py")

    assert "def hello_world" in path.read_text()


def test_deploy_function_file_accepts_target_directory(tmp_path):
    path = deploy_function_file(
        tmp_path,
        "custom_hello.py",
        "def custom_hello():\n    return 'Hi'\n",
        target_directory="scratch/tools",
    )

    assert path == (
        tmp_path
        / "ignition"
        / "script-python"
        / "fluxy_functions"
        / "scratch"
        / "tools"
        / "custom_hello"
        / "code.py"
    )
    assert path.exists()


def test_delete_function_file_removes_target_resource(tmp_path):
    path = deploy_builtin_function_file(tmp_path, "hello_world.py", target_directory="scratch")

    deleted_path = delete_function_file(tmp_path, "hello_world.py", target_directory="scratch")

    assert deleted_path == path.parent
    assert not deleted_path.exists()


def test_target_directory_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="relative path"):
        deploy_builtin_function_file(tmp_path, "hello_world.py", target_directory="../bad")
