import json
from pathlib import Path

import httpx
import pytest

from fluxy import (
    FluxyClient,
    HistorianPath,
    HistorianStreamPermanentError,
    HistorianStreamProtocolError,
)


class ChunkedStream(httpx.SyncByteStream):
    def __init__(self, content, sizes=(1, 2, 5, 3, 8)):
        self.content = content
        self.sizes = sizes

    def __iter__(self):
        offset = index = 0
        while offset < len(self.content):
            size = self.sizes[index % len(self.sizes)]
            yield self.content[offset : offset + size]
            offset += size
            index += 1


def record(**payload):
    return json.dumps(payload, separators=(",", ":")).encode() + b"\n"


def client_for(*records):
    content = b"".join(records)

    def handler(_request):
        return httpx.Response(
            200,
            headers={"content-type": "application/x-ndjson; charset=utf-8"},
            stream=ChunkedStream(content),
        )

    return FluxyClient("https://gateway", http_client=httpx.Client(transport=httpx.MockTransport(handler)))


HEADER = record(
    type="header", protocolVersion=1,
    paths=[{"seriesKey": "a", "tagpath": "[default]A"}], start=1000, end=2000,
)
POINT = {"seriesKey": "a", "tagpath": "[default]A", "timestamp": 1100, "value": 1.5, "quality": "Good", "valueType": "number"}
JAVA_COLUMNAR_FIXTURE = (
    Path(__file__).parents[1]
    / "ignition-module/gateway/src/test/resources/historian-columnar.ndjson"
)


def block(sequence, *points):
    names = ("seriesKey", "tagpath", "timestamp", "value", "quality", "valueType")
    return record(
        type="block", sequence=sequence, rowCount=len(points),
        columns={name: [point[name] for point in points] for name in names},
    )


def test_stream_parses_arbitrary_tcp_chunks_multiple_blocks_and_terminal():
    client = client_for(
        HEADER,
        block(0, POINT),
        block(1),
        record(type="terminal", sequence=2, ok=True, blockCount=2, pointCount=1),
    )
    with client.historian_stream([HistorianPath("a", "[default]A")], 1000, 2000, max_block_rows=2) as stream:
        blocks = list(stream)
    assert [block.sequence for block in blocks] == [0, 1]
    assert blocks[0].points[0].value == 1.5
    assert stream.terminal is not None


@pytest.mark.skipif(
    not JAVA_COLUMNAR_FIXTURE.is_file(),
    reason="Ignition module sources are intentionally excluded from the MIT Python distribution",
)
def test_python_client_consumes_java_columnar_compatibility_fixture():
    content = JAVA_COLUMNAR_FIXTURE.read_bytes()

    def handler(_request):
        return httpx.Response(
            200,
            headers={"content-type": "application/x-ndjson"},
            stream=ChunkedStream(content),
        )

    client = FluxyClient(
        "https://gateway",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with client.historian_stream(
        [HistorianPath("a", "[default]A")], 1000, 2000, max_block_rows=5000
    ) as stream:
        blocks = list(stream)

    assert [(point.value, point.quality, point.value_type) for point in blocks[0].points] == [
        (1.5, "Good", "number"),
        ("ok", "Bad_Stale", "string"),
    ]
    assert stream.terminal.point_count == 2


def test_empty_stream_is_valid():
    client = client_for(HEADER, record(type="terminal", sequence=0, ok=True, blockCount=0, pointCount=0))
    with client.historian_stream([HistorianPath("a", "[default]A")], 1000, 2000, max_block_rows=2) as stream:
        assert list(stream) == []


@pytest.mark.parametrize(
    "records, message",
    [
        ((HEADER, block(1)), "sequence"),
        ((HEADER, b"{bad json}\n"), "malformed"),
        ((HEADER, block(0)), "terminal"),
        ((HEADER, record(type="terminal", sequence=0, ok=True, blockCount=1, pointCount=0)), "counts"),
        ((HEADER, record(type="terminal", sequence=0, ok=True, blockCount=0, pointCount=0), block(0)), "after"),
    ],
)
def test_stream_rejects_sequence_malformed_missing_and_inconsistent_terminal(records, message):
    with client_for(*records).historian_stream(
        [HistorianPath("a", "[default]A")], 1000, 2000, max_block_rows=2
    ) as stream:
        with pytest.raises(HistorianStreamProtocolError, match=message):
            list(stream)


def test_terminal_error_is_stably_typed_and_does_not_expose_message():
    client = client_for(HEADER, record(type="terminal", sequence=0, ok=False, blockCount=0, pointCount=0, code="FAILED", error="secret", transient=False))
    with client.historian_stream([HistorianPath("a", "[default]A")], 1000, 2000, max_block_rows=2) as stream:
        with pytest.raises(HistorianStreamPermanentError) as caught:
            list(stream)
    assert "secret" not in str(caught.value)
