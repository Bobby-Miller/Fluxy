from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from fluxy.mcp.server import _to_wire, register_tools, selected_token


def test_register_tools_defaults_to_read_only():
    server = FakeServer()
    fx = FakeFluxy()

    register_tools(server, fx)

    assert "fluxy_ping" in server.tools
    assert "tag_read_blocking" in server.tools
    assert "tag_write_blocking" not in server.tools
    assert "tag_delete_tags" not in server.tools
    assert server.tools["fluxy_ping"]() == {"ok": True, "base_url": "http://example/system/webdev/flux"}
    assert server.tools["project_get_project_name"]() == "flux"


def test_register_tools_can_enable_write_and_destructive_tools():
    server = FakeServer()

    register_tools(server, FakeFluxy(), allow_writes=True, allow_destructive=True)

    assert "tag_write_blocking" in server.tools
    assert "tag_configure" in server.tools
    assert "tag_delete_tags" in server.tools


def test_mcp_tools_return_json_safe_payloads():
    server = FakeServer()

    register_tools(server, FakeFluxy())

    assert server.tools["ignition_get_version"]() == {"version": "8.3.0", "major": 8, "minor": 3}
    assert server.tools["tag_read_blocking"]("[default]A") == {
        "value": 1,
        "quality": "Good",
        "timestamp": None,
        "tag_path": "[default]A",
    }
    assert server.tools["device_list_devices"]() == [
        {"name": "Sim", "enabled": True, "state": "Connected", "driver": "Simulator", "payload": {}}
    ]


def test_selected_token_reads_token_file(tmp_path):
    token_file = tmp_path / "token.txt"
    token_file.write_text("secret\n", encoding="utf-8")

    assert selected_token(SimpleNamespace(token=None, token_file=token_file)) == "secret"


def test_selected_token_rejects_token_and_token_file(tmp_path):
    token_file = tmp_path / "token.txt"
    token_file.write_text("secret\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        selected_token(SimpleNamespace(token="secret", token_file=token_file))


def test_to_wire_converts_nested_dataclasses():
    assert _to_wire({"items": [Nested(Leaf("ok"))]}) == {"items": [{"leaf": {"value": "ok"}}]}


class FakeServer:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


class FakeFluxy:
    def __init__(self):
        self.client = SimpleNamespace(base_url="http://example/system/webdev/flux")
        self.util = FakeUtil()
        self.project = FakeProject()
        self.tag = FakeTag()
        self.opc = FakeOpc()
        self.device = FakeDevice()


class FakeUtil:
    def get_version(self, refresh=False):
        return IgnitionVersion("8.3.0", 8, 3)

    def get_modules(self):
        return [{"name": "WebDev"}]


class FakeProject:
    def get_project_name(self):
        return "flux"

    def get_project_names(self):
        return ["flux"]

    def request_scan(self):
        return RequestScanResult(True, "Project scan requested")


class FakeTag:
    def read_blocking(self, tag_paths, timeout=None):
        return QualifiedValue(1, "Good", tag_path=tag_paths if isinstance(tag_paths, str) else tag_paths[0])

    def browse(self, path=None, tag_filter=None):
        return [BrowseResult("A", "[default]A")]

    def get_configuration(self, path, recursive=False):
        return [{"path": path, "recursive": recursive}]

    def write_blocking(self, tag_paths, values, timeout=None):
        return WriteResult("Good", tag_path=tag_paths if isinstance(tag_paths, str) else tag_paths[0])

    def configure(self, tags, base_path=None, collision_policy="o"):
        return [ConfigureResult("Good", name=tags[0].get("name"))]

    def delete_tags(self, tag_paths):
        return DeleteResult("Good", tag_path=tag_paths if isinstance(tag_paths, str) else tag_paths[0])


class FakeOpc:
    def get_servers(self, include_disabled=False):
        return ["Ignition OPC UA Server"]

    def get_server_state(self, opc_server):
        return "Connected"

    def browse(self, opc_server=None, device=None, folder_path=None, opc_item_path=None):
        return [{"opcItemPath": "ns=1;s=Demo"}]


class FakeDevice:
    def list_devices(self):
        return [DeviceConnection("Sim", True, "Connected", "Simulator", {})]


@dataclass(frozen=True)
class IgnitionVersion:
    version: str
    major: int
    minor: int


@dataclass(frozen=True)
class RequestScanResult:
    ok: bool
    message: str


@dataclass(frozen=True)
class QualifiedValue:
    value: int
    quality: str
    timestamp: str | None = None
    tag_path: str | None = None


@dataclass(frozen=True)
class BrowseResult:
    name: str
    full_path: str


@dataclass(frozen=True)
class WriteResult:
    quality: str
    tag_path: str | None = None


@dataclass(frozen=True)
class ConfigureResult:
    quality: str
    name: str | None = None


@dataclass(frozen=True)
class DeleteResult:
    quality: str
    tag_path: str | None = None


@dataclass(frozen=True)
class DeviceConnection:
    name: str
    enabled: bool
    state: str
    driver: str
    payload: dict


@dataclass(frozen=True)
class Leaf:
    value: str


@dataclass(frozen=True)
class Nested:
    leaf: Leaf
