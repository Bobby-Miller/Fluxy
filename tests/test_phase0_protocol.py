import json

import httpx
import pytest

from fluxy import FluxyClient, FluxyError, FluxyTimeoutError, HistorianPath


def test_capabilities_and_normalized_historian_page():
    def handler(request):
        if request.url.path.endswith("/capabilities"):
            return httpx.Response(
                200,
                json={
                    "ok": True,
                    "protocolVersion": 1,
                    "historianPage": {
                        "supported": True,
                        "exactRawCapture": True,
                        "defaultLimit": 1000,
                        "maxLimit": 10000,
                        "maxPaths": 25,
                        "maxWindowMs": 300000,
                        "equalTimestampPaging": "composite-cursor",
                    },
                },
            )
        assert json.loads(request.content) == {
            "paths": [{"seriesKey": "tank.level", "tagpath": "[default]Tank/Level"}],
            "start": 1000,
            "end": 2000,
            "limit": 2,
        }
        return httpx.Response(
            200,
            json={
                "ok": True,
                "protocolVersion": 1,
                "paths": [{"seriesKey": "tank.level", "tagpath": "[default]Tank/Level"}],
                "start": 1000,
                "end": 2000,
                "points": [
                    {"seriesKey": "tank.level", "tagpath": "[default]Tank/Level", "timestamp": 1100, "value": 12.5, "quality": "Good", "valueType": "number"}
                ],
                "complete": False,
                "nextCursor": "opaque-v1",
            },
        )

    client = FluxyClient(
        "https://gateway/data", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert client.capabilities().exact_raw_capture is True
    assert client.capabilities().max_paths == 25
    page = client.historian_page(
        [HistorianPath("tank.level", "[default]Tank/Level")], 1000, 2000, limit=2
    )
    assert page.points[0].value == 12.5
    assert page.points[0].series_key == "tank.level"
    assert page.next_cursor == "opaque-v1"


def test_historian_browse_preserves_continuation():
    def handler(request):
        return httpx.Response(
            200,
            json={"ok": True, "results": [], "continuationPoint": "opaque-next", "quality": "Good"},
        )

    client = FluxyClient(
        "https://gateway/data", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    page = client.historian_browse("histprov:Core Historian:/")
    assert page.continuation_point == "opaque-next"
    assert page.quality == "Good"


def test_typed_http_error_exposes_status_and_code():
    def handler(request):
        return httpx.Response(
            409, json={"ok": False, "code": "HISTORIAN_PAGE_UNSAFE", "error": "unsafe"}
        )

    client = FluxyClient(
        "https://gateway/data", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(FluxyError) as caught:
        client.historian_page([HistorianPath("key", "[default]Tag")], 1, 2)
    assert caught.value.status_code == 409
    assert caught.value.code == "HISTORIAN_PAGE_UNSAFE"


def test_historian_page_sends_multiple_paths_and_opaque_cursor():
    def handler(request):
        payload = json.loads(request.content)
        assert payload["paths"] == [
            {"seriesKey": "a", "tagpath": "[default]A"},
            {"seriesKey": "b", "tagpath": "[default]B"},
        ]
        assert payload["cursor"] == "opaque"
        return httpx.Response(200, json={
            "ok": True, "paths": payload["paths"], "start": 0, "end": 300000,
            "points": [], "complete": True, "nextCursor": None,
        })

    client = FluxyClient(
        "https://gateway/data", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    page = client.historian_page(
        [HistorianPath("a", "[default]A"), HistorianPath("b", "[default]B")],
        0, 300000, cursor="opaque",
    )
    assert page.complete


def test_timeout_is_typed():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    client = FluxyClient(
        "https://gateway/data", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(FluxyTimeoutError):
        client.capabilities()
