# Historian Page Protocol v1

Phase 0 exposes `POST /fluxy/capabilities` and `POST /fluxy/historian/page`.
The caller owns a stable `seriesKey` and sends only a fully qualified realtime Ignition
tag path (`[provider]relative/path`). The Gateway resolves the provider once through
Ignition's historical namespace and queries the unique matching driver route. Fluxy does
not accept physical routing input. A full `histprov:` path is accepted only as a diagnostic
escape hatch.

## Request

```json
{"paths":[{"seriesKey":"tank.level","tagpath":"[default]Tank/Level"}],"start":1000,"end":2000,"limit":1000,"cursor":"eyJ2IjoxLC4uLn0"}
```

`start` and `end` are Unix epoch milliseconds. The interval is strictly `[start,end)`,
must not exceed 86,400,000 ms (one day), and accepts at most 20 unique `seriesKey` entries. `limit`
defaults to 1000 and must be between 1 and 10000. The versioned cursor is opaque and is
bound by SHA-256 to the ordered path list and window; clients return it unchanged.

## Response

```json
{"ok":true,"protocolVersion":1,"paths":[{"seriesKey":"tank.level","tagpath":"[default]Tank/Level"}],"start":1000,"end":2000,"points":[{"seriesKey":"tank.level","tagpath":"[default]Tank/Level","timestamp":1100,"value":12.5,"quality":"Good","valueType":"number"}],"complete":true,"nextCursor":null}
```

After path resolution, the first page calls public `system.tag.queryTagCalculations` once
for `Count`, with no bounding values, no interpolation, and `ignoreBadQuality=true`. Fluxy
accepts zero or one valid non-negative integral Count row per resolved path, treating an
omitted expected alias as Count zero. It sums the returned per-path counts conservatively
before duplicate timestamp normalization and fails closed
if Count is unavailable, malformed, or exceeds 10,000. Count overflow is the only
splittable admission failure and returns HTTP 400 with stable code
`HISTORIAN_COUNT_LIMIT_EXCEEDED`; unavailable or malformed Count remains a generic 400.
Only then does it query all paths
in one `system.tag.queryTagHistory` call with `returnSize=-1`, `Tall`, no bounding values,
no interpolation, and `ignoreBadQuality=true`. Admission and returned points therefore
share Ignition's Good/192 eligibility policy; bad-quality samples are not returned.
It filters strict boundaries, then orders by `(timestamp,seriesKey)`. If Ignition returns
multiple rows for the QuestDB identity `(seriesKey,timestamp)`, the last Tall row returned
by Ignition wins. More than 10,000 normalized points is rejected. The immutable normalized
result is retained for up to 20 seconds in an LRU bounded to 8 windows, 40,000
points, and 16 MiB. Continuations only read that snapshot; a missing or expired snapshot
fails explicitly and never re-queries. Completed consumers leave it available for other
consumers until TTL/LRU eviction. The cursor binds the request fingerprint, offset, and
boundary identity, safely splitting equal timestamps.
`complete=false` always includes `nextCursor`.

Cache critical sections cover only TTL/LRU bookkeeping. Namespace browse, Count, and raw
history IO run outside the global cache lock. Per-fingerprint in-flight coordination lets
unrelated windows query concurrently while concurrent duplicate first pages share one
materialized result (or the same fail-closed error).

Resolution browses historical provider roots in blocks, skips unavailable history
providers, and caches at most 128 tag-provider routes for 60 seconds. A cache miss refreshes
the namespace and fails closed when no driver or more than one driver has the requested
tag-provider suffix. Resolved physical paths are never echoed; response paths and points
retain the caller's original tag paths.

## Capabilities

Ignition 8.1.50 and 8.3.4 advertise `supported=true`, `exactRawCapture=true`,
`maxPaths=20`, `maxWindowMs=86400000`, `maxLimit=10000`, `maxTotalPoints=10000`, and
snapshot-backed composite cursor paging.
This relies on the documented `returnSize=-1` on-change mode. `tagpathResolution` describes
the Ignition-owned namespace resolution. The 8.3 module advertises historian paging as
unsupported if its public `system.historian.browse` capability is unavailable.

## Native stream

Protocol v1 optionally advertises `historianStream` with `supported`,
`protocolVersion: 1`, `format: ndjson-columnar-blocks`, and a positive `maxBlockRows`. Clients that do not see a
supported stream capability continue to use historian paging. The request uses the page
request's `paths`, `start`, and `end` fields and is sent to `POST /fluxy/historian/stream`.
The response media type is `application/x-ndjson`; each JSON object is followed by one LF.

The first record is exactly a request-echoing header:

```json
{"type":"header","protocolVersion":1,"paths":[{"seriesKey":"tank.level","tagpath":"[default]Tank/Level"}],"start":1000,"end":2000}
```

Zero or more blocks follow. Sequence numbers are contiguous from zero, each block contains
at most `maxBlockRows`, and every named column has exactly `rowCount` entries. Rows retain
all historian qualities. The stream does not guarantee global timestamp or series ordering:

```json
{"type":"block","sequence":0,"rowCount":1,"columns":{"seriesKey":["tank.level"],"tagpath":["[default]Tank/Level"],"timestamp":[1100],"value":[12.5],"quality":["Good"],"valueType":["number"]}}
```

Success requires exactly one final terminal whose sequence and counts cover all preceding
blocks. An empty result is a header followed by a zero-count terminal. EOF before terminal,
records after terminal, malformed records, sequence gaps, and count mismatches invalidate
the entire logical transfer:

```json
{"type":"terminal","sequence":1,"ok":true,"blockCount":1,"pointCount":1}
```

An error terminal has `ok:false` and includes `code`, `error`, and `transient`; it never
commits coverage. Consumers may persist already acknowledged blocks, but must advance a
coverage cursor only after the valid success terminal and acknowledgement of every block.
Retries are safe where the destination uses the canonical `(series_id,timestamp)` dedup key.
