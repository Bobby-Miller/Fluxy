import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).parents[1]
DISPATCHERS = [
    ROOT / "ignition-module/gateway/src/main/resources/fluxy_dispatch.py",
    ROOT / "ignition-module/gateway81/src/main/resources/fluxy_dispatch.py",
]
pytestmark = pytest.mark.skipif(
    not all(path.is_file() for path in DISPATCHERS),
    reason="Ignition module sources are intentionally excluded from the MIT Python distribution",
)


class Dataset:
    def __init__(self, columns, rows):
        self.columns = columns
        self.rows = rows

    def getColumnNames(self):
        return self.columns

    def getRowCount(self):
        return len(self.rows)

    def getValueAt(self, row, column):
        return self.rows[row][self.columns.index(column)]


class Util:
    @staticmethod
    def jsonEncode(value):
        return json.dumps(value)

    @staticmethod
    def jsonDecode(value):
        return json.loads(value)


def load_dispatcher(
    path,
    counts,
    raw_rows=(),
    calculation_error=None,
    raw_hook=None,
    count_columns=("Path", "Count"),
):
    calls = {"count": 0, "raw": 0, "count_kwargs": [], "raw_kwargs": []}

    def query_calculations(**kwargs):
        calls["count"] += 1
        calls["count_kwargs"].append(kwargs)
        if calculation_error:
            raise calculation_error
        rows = counts(kwargs) if callable(counts) else counts
        return Dataset(list(count_columns), rows)

    def query_history(**kwargs):
        calls["raw"] += 1
        calls["raw_kwargs"].append(kwargs)
        if raw_hook:
            raw_hook()
        return Dataset(["Timestamp", "Value", "Quality", "Path"], raw_rows)

    system = SimpleNamespace(
        date=SimpleNamespace(fromMillis=lambda value: value),
        tag=SimpleNamespace(
            queryTagCalculations=query_calculations,
            queryTagHistory=query_history,
        ),
        util=Util(),
    )
    source = path.read_text()
    source = source.replace(
        "except HistorianCountLimitExceeded, exc:",
        "except HistorianCountLimitExceeded as exc:",
    )
    source = source.replace("except BadRequest, exc:", "except BadRequest as exc:")
    source = source.replace("except Conflict, exc:", "except Conflict as exc:")
    source = source.replace("except Exception, exc:", "except Exception as exc:")
    module = {"system": system, "long": int, "basestring": str, "__name__": "dispatcher_test"}
    exec(compile(source, str(path), "exec"), module)
    module["_history_resolution_supported"] = lambda: True
    module["_resolve_history_paths"] = lambda paths: [
        item["tagpath"] + "-resolved" for item in paths
    ]
    return module, calls


def request(key="a", tagpath="[default]A", limit=1000):
    return {
        "paths": [{"seriesKey": key, "tagpath": tagpath}],
        "start": 0,
        "end": 1000,
        "limit": limit,
    }


@pytest.mark.parametrize("path", DISPATCHERS)
def test_count_over_limit_prevents_raw_query_and_exact_limit_is_allowed(path):
    module, calls = load_dispatcher(path, [["a", 10001]])
    with pytest.raises(module["BadRequest"], match="Count exceeds"):
        module["_historian_page"](request())
    assert calls["raw"] == 0

    module, calls = load_dispatcher(path, [["a", 10000]])
    assert module["_historian_page"](request())["complete"] is True
    assert calls["raw"] == 1


@pytest.mark.parametrize("path", DISPATCHERS)
def test_accepts_twenty_paths_and_one_day_and_advertises_limits(path):
    payload = request()
    payload["paths"] = [
        {"seriesKey": "s%d" % index, "tagpath": "[default]Tag%d" % index}
        for index in range(20)
    ]
    payload["end"] = 86400000
    module, calls = load_dispatcher(path, [])

    assert module["_historian_page"](payload)["complete"] is True
    assert calls["raw_kwargs"][0]["returnSize"] == -1
    capability = module["_capabilities"]({})["historianPage"]
    assert capability["maxPaths"] == 20
    assert capability["maxWindowMs"] == 86400000
    assert capability["maxTotalPoints"] == 10000


@pytest.mark.parametrize("path", DISPATCHERS)
def test_count_overflow_dispatch_has_stable_code_but_malformed_count_does_not(path):
    module, _calls = load_dispatcher(path, [["a", 10001]])
    overflow = json.loads(module["dispatch"]("historian/page", json.dumps(request())))
    assert overflow["status"] == 400
    assert overflow["body"]["code"] == "HISTORIAN_COUNT_LIMIT_EXCEEDED"

    module, _calls = load_dispatcher(path, [["wrong", 1]])
    malformed = json.loads(module["dispatch"]("historian/page", json.dumps(request())))
    assert malformed["status"] == 400
    assert "code" not in malformed["body"]


@pytest.mark.parametrize("path", DISPATCHERS)
@pytest.mark.parametrize(
    "counts,error", [([["wrong", 1]], None), ([], RuntimeError("no Count"))]
)
def test_count_malformed_or_error_fails_closed(path, counts, error):
    module, calls = load_dispatcher(path, counts, calculation_error=error)
    with pytest.raises(module["BadRequest"], match="unavailable or malformed"):
        module["_historian_page"](request())
    assert calls["raw"] == 0


@pytest.mark.parametrize("path", DISPATCHERS)
@pytest.mark.parametrize(
    "columns", [("path", "Count"), ("tagpath", "COUNT"), ("identity", "count")]
)
def test_count_accepts_documented_and_unique_identity_columns(path, columns):
    module, calls = load_dispatcher(path, [["a", 1]], count_columns=columns)
    assert module["_historian_page"](request())["complete"] is True
    assert calls["raw"] == 1
    assert calls["count_kwargs"][0]["aliases"] == ["a"]


@pytest.mark.parametrize("path", DISPATCHERS)
def test_count_alias_identity_allows_reordering_and_omitted_zero_rows(path):
    payload = request()
    payload["paths"].append({"seriesKey": "b", "tagpath": "[default]B"})

    module, calls = load_dispatcher(path, [["b", 1], ["a", 1]])
    assert module["_historian_page"](payload)["complete"] is True
    assert calls["count_kwargs"][0]["aliases"] == ["a", "b"]

    module, calls = load_dispatcher(path, [["a", 1]])
    assert module["_historian_page"](payload)["complete"] is True
    assert calls["raw"] == 1


@pytest.mark.parametrize("path", DISPATCHERS)
def test_count_accepts_all_omitted_rows_as_zero_with_valid_columns(path):
    module, calls = load_dispatcher(path, [])
    assert module["_historian_page"](request())["complete"] is True
    assert calls["raw"] == 1


@pytest.mark.parametrize("path", DISPATCHERS)
@pytest.mark.parametrize("rows", [[["a", 1], ["a", 1]], [["unexpected", 1]]])
def test_count_rejects_duplicate_or_unexpected_alias_rows(path, rows):
    module, calls = load_dispatcher(path, rows)
    with pytest.raises(module["BadRequest"], match="unavailable or malformed"):
        module["_historian_page"](request())
    assert calls["raw"] == 0


@pytest.mark.parametrize("path", DISPATCHERS)
@pytest.mark.parametrize(
    ("columns", "rows"),
    [
        (("path", "tagpath", "Count"), [["a", "a", 1]]),
        (("Count",), [[1]]),
        (("path",), [["a"]]),
        (("path", "Count", "extra"), [["a", 1, "x"]]),
        (("path", "Count"), [["[default]A-resolved", 1], ["unexpected", 1]]),
    ],
)
def test_count_rejects_ambiguous_missing_or_extra_columns_and_rows(path, columns, rows):
    module, calls = load_dispatcher(path, rows, count_columns=columns)
    with pytest.raises(module["BadRequest"], match="unavailable or malformed"):
        module["_historian_page"](request())
    assert calls["raw"] == 0


@pytest.mark.parametrize("path", DISPATCHERS)
@pytest.mark.parametrize("columns", [("path",), ("Count",), ("path", "Count", "extra")])
def test_count_rejects_malformed_empty_dataset_shape(path, columns):
    module, calls = load_dispatcher(path, [], count_columns=columns)
    with pytest.raises(module["BadRequest"], match="unavailable or malformed"):
        module["_historian_page"](request())
    assert calls["raw"] == 0


@pytest.mark.parametrize("path", DISPATCHERS)
@pytest.mark.parametrize("count", [-1, 1.5, "1", None, True])
def test_count_rejects_non_numeric_negative_or_fractional_values(path, count):
    module, calls = load_dispatcher(path, [["a", count]])
    with pytest.raises(module["BadRequest"], match="unavailable or malformed"):
        module["_historian_page"](request())
    assert calls["raw"] == 0


@pytest.mark.parametrize("path", DISPATCHERS)
def test_count_and_raw_query_share_good_quality_policy_and_count_is_conservative(path):
    counts = [["b", 4001], ["a", 6000]]
    module, calls = load_dispatcher(path, counts)
    payload = request()
    payload["paths"].append({"seriesKey": "b", "tagpath": "[default]A"})
    with pytest.raises(module["BadRequest"], match="Count exceeds"):
        module["_historian_page"](payload)
    assert calls["raw"] == 0
    assert calls["count_kwargs"][0]["ignoreBadQuality"] is True
    assert calls["count_kwargs"][0]["includeBoundingValues"] is False
    assert calls["count_kwargs"][0]["noInterpolation"] is True
    assert calls["count_kwargs"][0]["aliases"] == ["a", "b"]

    module, calls = load_dispatcher(
        path,
        [["a", 2]],
        [[100, 1, "Good", "a"], [100, 2, "Good", "a"]],
    )
    result = module["_historian_page"](request())
    assert len(result["points"]) == 1
    assert result["points"][0]["value"] == 2
    assert calls["raw_kwargs"][0]["ignoreBadQuality"] is True


@pytest.mark.parametrize("path", DISPATCHERS)
def test_unrelated_windows_run_concurrently_and_duplicate_first_pages_share_io(path):
    barrier = threading.Barrier(2)
    module, calls = load_dispatcher(
        path,
        lambda kwargs: [[kwargs["aliases"][0], 0]],
        raw_hook=lambda: barrier.wait(timeout=2),
    )
    errors = []

    def run(payload):
        try:
            module["_historian_page"](payload)
        except Exception as error:
            errors.append(error)

    first = threading.Thread(target=run, args=(request("a", "[default]A"),))
    second = threading.Thread(target=run, args=(request("b", "[default]B"),))
    first.start()
    second.start()
    first.join(3)
    second.join(3)
    assert not errors
    assert calls["raw"] == 2

    entered = threading.Event()
    release = threading.Event()

    def block_once():
        entered.set()
        assert release.wait(2)

    module, calls = load_dispatcher(path, [["a", 0]], raw_hook=block_once)
    first = threading.Thread(target=run, args=(request(),))
    second = threading.Thread(target=run, args=(request(),))
    first.start()
    assert entered.wait(1)
    second.start()
    release.set()
    first.join(3)
    second.join(3)
    assert calls["count"] == 1
    assert calls["raw"] == 1


@pytest.mark.parametrize("path", DISPATCHERS)
def test_coalesced_callers_with_different_limits_share_a_usable_snapshot(path):
    entered = threading.Event()
    release = threading.Event()

    def block_once():
        entered.set()
        assert release.wait(2)

    rows = [[100 + index, index, "Good", "a"] for index in range(3)]
    module, calls = load_dispatcher(path, [["a", 3]], rows, raw_hook=block_once)
    results = {}

    def run(key, payload):
        results[key] = module["_historian_page"](payload)

    owner = threading.Thread(target=run, args=("owner", request(limit=10)))
    waiter = threading.Thread(target=run, args=("waiter", request(limit=1)))
    owner.start()
    assert entered.wait(1)
    waiter.start()
    release.set()
    owner.join(3)
    waiter.join(3)

    assert results["owner"]["complete"] is True
    assert results["waiter"]["complete"] is False
    continuation = module["_historian_page"](
        dict(request(limit=1), cursor=results["waiter"]["nextCursor"])
    )
    assert len(continuation["points"]) == 1
    assert calls["raw"] == 1
