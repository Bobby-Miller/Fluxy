from pathlib import Path
from types import SimpleNamespace
import json
import threading

import pytest


ROOT = Path(__file__).parents[1]
DISPATCHERS = [
    ROOT / "ignition-module/gateway81/src/main/resources/fluxy_dispatch.py",
    ROOT / "ignition-module/gateway/src/main/resources/fluxy_dispatch.py",
]
pytestmark = pytest.mark.skipif(
    not all(path.is_file() for path in DISPATCHERS),
    reason="Ignition module sources are intentionally excluded from the MIT Python distribution",
)


class BrowseResult:
    def __init__(self, path):
        self.path = path

    def getPath(self):
        return self.path


class BrowseResults:
    def __init__(self, paths):
        self.paths = paths

    def getResults(self):
        return [BrowseResult(path) for path in self.paths]


class Dataset:
    columns = ["path", "value", "quality", "timestamp"]

    def getColumnNames(self):
        return self.columns

    def __init__(self, rows=None):
        self.rows = rows or [{"path": "series", "value": 42.5, "quality": "Good", "timestamp": 1500}]

    def getRowCount(self):
        return len(self.rows)

    def getValueAt(self, row, column):
        return self.rows[row][column]


class CalculationDataset(Dataset):
    columns = ["Path", "Count"]


class Date:
    @staticmethod
    def fromMillis(value):
        return value


def load_dispatcher(path, routes, offline=(), rows=None):
    calls = []

    def browse(value):
        calls.append(value)
        if value in offline:
            raise RuntimeError("offline")
        result = routes.get(value)
        return None if result is None else BrowseResults(result)

    query_calls = []

    def query(**kwargs):
        query_calls.append(kwargs)
        return Dataset(rows)

    def calculations(**kwargs):
        source_rows = Dataset(rows).rows
        counts = []
        for path, alias in zip(kwargs["paths"], kwargs["aliases"], strict=True):
            identity = path.rsplit(":", 1)[-1]
            matching = [row for row in source_rows if str(row["path"]) == identity]
            count = len(matching) if matching else len(source_rows) if len(kwargs["paths"]) == 1 else 0
            counts.append({"Path": alias, "Count": count})
        return CalculationDataset(counts)

    util = SimpleNamespace(
        jsonEncode=lambda value: json.dumps(value, separators=(",", ":")),
        jsonDecode=lambda value: json.loads(value),
    )
    system = SimpleNamespace(
        date=Date(),
        tag=SimpleNamespace(queryTagCalculations=calculations, queryTagHistory=query),
        util=util,
    )
    if "gateway81" in str(path):
        system.tag.browseHistoricalTags = browse
    else:
        system.historian = SimpleNamespace(browse=browse)
    namespace = {"system": system, "basestring": str, "long": int}
    source = path.read_text().split("\ndef dispatch(", 1)[0]
    exec(compile(source, str(path), "exec"), namespace)
    return namespace, calls, query_calls


@pytest.mark.parametrize("dispatcher", DISPATCHERS)
def test_page_resolves_unique_route_once_and_echoes_original_path(dispatcher):
    namespace, browse_calls, query_calls = load_dispatcher(
        dispatcher,
        {
            "": ["histprov:offline", "histprov:IgnitionDB_Hist"],
            "histprov:IgnitionDB_Hist": [
                "histprov:IgnitionDB_Hist:/drv:ignition-uppdl-igntag-04:tag_04"
            ],
        },
        offline=("histprov:offline",),
    )
    payload = {
        "paths": [{"seriesKey": "series", "tagpath": "[tag_04]Area/Value"}],
        "start": 1000,
        "end": 2000,
    }

    first = namespace["_historian_page"](payload)
    second = namespace["_historian_page"](payload)

    expected = (
        "histprov:IgnitionDB_Hist:/drv:ignition-uppdl-igntag-04:tag_04:/tag:Area/Value"
    )
    assert query_calls[0]["paths"] == [expected]
    assert query_calls[0]["returnSize"] == -1
    assert query_calls[0]["columnNames"] == ["series"]
    assert first["paths"] == payload["paths"]
    assert first["points"][0]["tagpath"] == "[tag_04]Area/Value"
    assert second["points"][0]["value"] == 42.5
    assert browse_calls.count("") == 1


@pytest.mark.parametrize("dispatcher", DISPATCHERS)
@pytest.mark.parametrize(
    "drivers",
    [
        [],
        [
            "histprov:a:/drv:gateway:default",
            "histprov:a:/drv:remote:default",
        ],
    ],
)
def test_page_fails_closed_without_one_route(dispatcher, drivers):
    namespace, _browse_calls, query_calls = load_dispatcher(
        dispatcher, {"": ["histprov:a"], "histprov:a": drivers}
    )
    payload = {
        "paths": [{"seriesKey": "series", "tagpath": "[default]Tag"}],
        "start": 1000,
        "end": 2000,
    }

    with pytest.raises(namespace["BadRequest"], match="No unique historical driver route"):
        namespace["_historian_page"](payload)
    assert query_calls == []


@pytest.mark.parametrize("dispatcher", DISPATCHERS)
def test_full_historical_path_is_diagnostic_passthrough(dispatcher):
    namespace, browse_calls, query_calls = load_dispatcher(dispatcher, {})
    historical = "histprov:test:/drv:gateway:default:/tag:Tag"
    namespace["_historian_page"](
        {
            "paths": [{"seriesKey": "series", "tagpath": historical}],
            "start": 1000,
            "end": 2000,
        }
    )

    assert browse_calls == []
    assert query_calls[0]["paths"] == [historical]


@pytest.mark.parametrize("dispatcher", DISPATCHERS)
def test_page_rejects_physical_routing_input(dispatcher):
    namespace, _browse_calls, query_calls = load_dispatcher(dispatcher, {})
    payload = {
        "paths": [{"seriesKey": "series", "tagpath": "gateway:default:/tag:Tag"}],
        "start": 1000,
        "end": 2000,
    }

    with pytest.raises(namespace["BadRequest"], match="fully qualified"):
        namespace["_historian_page"](payload)
    assert query_calls == []


@pytest.mark.parametrize("dispatcher", DISPATCHERS)
def test_four_pages_use_one_query_without_duplicate_or_loss(dispatcher):
    rows = []
    for timestamp in range(1000, 1004):
        rows.extend(
            {"path": key, "value": "%s-%s" % (key, timestamp), "quality": "Good", "timestamp": timestamp}
            for key in ("a", "b")
        )
    # The last Tall row deterministically replaces the prior identity.
    rows.insert(1, {"path": "a", "value": "loser", "quality": "Good", "timestamp": 1000})
    namespace, _browse, query_calls = load_dispatcher(dispatcher, {}, rows=rows)
    payload = {
        "paths": [
            {"seriesKey": "a", "tagpath": "histprov:x:/drv:y:/tag:a"},
            {"seriesKey": "b", "tagpath": "histprov:x:/drv:y:/tag:b"},
        ],
        "start": 1000,
        "end": 2000,
        "limit": 2,
    }
    points = []
    response = namespace["_historian_page"](payload)
    concurrent_cursor = response["nextCursor"]
    while True:
        points.extend(response["points"])
        if response["complete"]:
            break
        response = namespace["_historian_page"](dict(payload, cursor=response["nextCursor"]))

    assert len(query_calls) == 1
    assert [(point["timestamp"], point["seriesKey"]) for point in points] == [
        (timestamp, key) for timestamp in range(1000, 1004) for key in ("a", "b")
    ]
    assert points[0]["value"] == "loser"
    concurrent_page = namespace["_historian_page"](dict(payload, cursor=concurrent_cursor))
    assert len(concurrent_page["points"]) == 2
    assert len(query_calls) == 1
    assert namespace["_HISTORY_PAGE_CACHE"]


@pytest.mark.parametrize("dispatcher", DISPATCHERS)
def test_cursor_cache_miss_and_expiration_never_requery(dispatcher):
    rows = [
        {"path": "series", "value": index, "quality": "Good", "timestamp": 1000 + index}
        for index in range(3)
    ]
    namespace, _browse, query_calls = load_dispatcher(dispatcher, {}, rows=rows)
    payload = {
        "paths": [{"seriesKey": "series", "tagpath": "histprov:x:/drv:y:/tag:z"}],
        "start": 1000, "end": 2000, "limit": 1,
    }
    first = namespace["_historian_page"](payload)
    namespace["_HISTORY_PAGE_CACHE"].clear()
    namespace["_HISTORY_PAGE_CACHE_ORDER"][:] = []
    with pytest.raises(namespace["BadRequest"], match="missing or expired"):
        namespace["_historian_page"](dict(payload, cursor=first["nextCursor"]))
    assert len(query_calls) == 1

    first = namespace["_historian_page"](payload)
    key = namespace["_HISTORY_PAGE_CACHE_ORDER"][0]
    saved = namespace["_HISTORY_PAGE_CACHE"][key]
    namespace["_HISTORY_PAGE_CACHE"][key] = (0, saved[1], saved[2])
    with pytest.raises(namespace["BadRequest"], match="missing or expired"):
        namespace["_historian_page"](dict(payload, cursor=first["nextCursor"]))
    assert len(query_calls) == 2


@pytest.mark.parametrize("dispatcher", DISPATCHERS)
def test_rejects_oversize_normalized_result(dispatcher):
    rows = [
        {"path": "series", "value": index, "quality": "Good", "timestamp": index}
        for index in range(10001)
    ]
    namespace, _browse, query_calls = load_dispatcher(dispatcher, {}, rows=rows)
    with pytest.raises(namespace["BadRequest"], match="exceeds 10000"):
        namespace["_historian_page"]({
            "paths": [{"seriesKey": "series", "tagpath": "histprov:x:/drv:y:/tag:z"}],
            "start": 0, "end": 10001, "limit": 1000,
        })
    assert len(query_calls) == 0
    assert namespace["_HISTORY_PAGE_CACHE"] == {}


@pytest.mark.parametrize("dispatcher", DISPATCHERS)
def test_concurrent_first_page_coalesces_and_lru_evicts(dispatcher):
    rows = [
        {"path": "series", "value": index, "quality": "Good", "timestamp": 1000 + index}
        for index in range(3)
    ]
    namespace, _browse, query_calls = load_dispatcher(dispatcher, {}, rows=rows)
    namespace["_HISTORY_PAGE_CACHE_MAX_WINDOWS"] = 1
    base = {
        "paths": [{"seriesKey": "series", "tagpath": "histprov:x:/drv:y:/tag:z"}],
        "start": 1000, "end": 2000, "limit": 1,
    }
    results = []
    threads = [threading.Thread(target=lambda: results.append(namespace["_historian_page"](base))) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(results) == 4
    assert len(query_calls) == 1

    namespace["_historian_page"](dict(base, start=999, end=2000))
    assert len(namespace["_HISTORY_PAGE_CACHE"]) == 1
    with pytest.raises(namespace["BadRequest"], match="missing or expired"):
        namespace["_historian_page"](dict(base, cursor=results[0]["nextCursor"]))
    assert len(query_calls) == 2
