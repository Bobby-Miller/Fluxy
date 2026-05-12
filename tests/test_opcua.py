import json

import httpx

from fluxy import Fluxy, FluxyClient


def test_opcua_add_connection_posts_connection_payload():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/opcua/addConnection"
        assert json.loads(request.content) == {
            "name": "Flux Field",
            "description": "Flux Field OPC UA simulator",
            "discoveryUrl": "opc.tcp://localhost:4840/flux/field",
            "endpointUrl": "opc.tcp://localhost:4840/flux/field",
            "securityPolicy": "None",
            "securityMode": "None",
            "settings": {"ENABLED": True, "CERTIFICATEVALIDATIONENABLED": False},
        }
        return httpx.Response(200, json={"ok": True, "name": "Flux Field"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.opcua_add_connection(
        "Flux Field",
        "Flux Field OPC UA simulator",
        "opc.tcp://localhost:4840/flux/field",
        "opc.tcp://localhost:4840/flux/field",
        settings={"ENABLED": True, "CERTIFICATEVALIDATIONENABLED": False},
    )


def test_opcua_remove_connection_posts_name():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/opcua/removeConnection"
        assert json.loads(request.content) == {"name": "Flux Field"}
        return httpx.Response(200, json={"ok": True, "name": "Flux Field"})

    client = FluxyClient(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert client.opcua_remove_connection("Flux Field")


def test_fluxy_opcua_namespace_delegates_to_client():
    def handler(request):
        assert request.url.path == "/system/webdev/Fluxy/fluxy/opcua/addConnection"
        return httpx.Response(200, json={"ok": True})

    fx = Fluxy(
        "https://ignition.example/system/webdev/Fluxy",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert fx.opcua.add_connection(
        "Flux Field",
        "Flux Field OPC UA simulator",
        "opc.tcp://localhost:4840/flux/field",
        "opc.tcp://localhost:4840/flux/field",
    )
