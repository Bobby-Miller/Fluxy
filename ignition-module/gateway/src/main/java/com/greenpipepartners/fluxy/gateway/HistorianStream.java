/*
 * SPDX-FileCopyrightText: 2026 Green Pipe Partners, LLC
 * SPDX-License-Identifier: MPL-2.0
 */
package com.greenpipepartners.fluxy.gateway;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.inductiveautomation.ignition.common.Path;
import com.inductiveautomation.ignition.common.QualifiedPath;
import com.inductiveautomation.ignition.common.StreamingDatasetWriter;
import com.inductiveautomation.ignition.common.browsing.BrowseFilter;
import com.inductiveautomation.ignition.common.gson.JsonArray;
import com.inductiveautomation.ignition.common.gson.JsonElement;
import com.inductiveautomation.ignition.common.gson.JsonNull;
import com.inductiveautomation.ignition.common.gson.JsonObject;
import com.inductiveautomation.ignition.common.gson.JsonParser;
import com.inductiveautomation.ignition.common.gson.JsonPrimitive;
import com.inductiveautomation.ignition.common.model.values.QualityCode;
import com.inductiveautomation.ignition.common.sqltags.history.BasicTagHistoryQueryParams;
import com.inductiveautomation.ignition.common.sqltags.history.ReturnFormat;
import com.inductiveautomation.ignition.common.sqltags.history.TagHistoryQueryFlags;
import com.inductiveautomation.ignition.common.util.Flags;

final class HistorianStream {
    static final int MAX_PATHS = 20;
    static final long MAX_WINDOW_MS = 86_400_000L;
    static final int MAX_BLOCK_ROWS = 5000;
    static final int MAX_BLOCK_BYTES = 1_048_576;
    static final long MAX_RESPONSE_BYTES = 64L * 1_048_576L;
    static final long MAX_DURATION_MS = 120_000L;
    private static final int TERMINAL_RESERVE_BYTES = 4096;
    private static final Set<String> REQUEST_FIELDS = Set.of("paths", "start", "end");
    private static final long ROUTE_CACHE_TTL_MS = 60_000L;
    private static final int ROUTE_CACHE_MAX = 128;
    private static final Map<String, CachedRoute> ROUTE_CACHE = new LinkedHashMap<>();

    private HistorianStream() {
    }

    static Request parse(String body) {
        JsonObject payload;
        try {
            payload = JsonParser.parseString(body).getAsJsonObject();
        } catch (Exception exception) {
            throw new BadRequest("request body must be a JSON object");
        }
        for (String key : payload.keySet()) {
            if (!REQUEST_FIELDS.contains(key)) {
                throw new BadRequest("historian stream request contains unsupported fields");
            }
        }
        if (!payload.has("paths") || !payload.get("paths").isJsonArray()) {
            throw new BadRequest("paths must contain between 1 and 20 items");
        }
        JsonArray paths = payload.getAsJsonArray("paths");
        if (paths.size() < 1 || paths.size() > MAX_PATHS) {
            throw new BadRequest("paths must contain between 1 and 20 items");
        }
        List<RequestedPath> requested = new ArrayList<>();
        Set<String> keys = new HashSet<>();
        for (JsonElement element : paths) {
            if (!element.isJsonObject()) {
                throw new BadRequest("each path must contain only seriesKey and tagpath");
            }
            JsonObject item = element.getAsJsonObject();
            if (item.size() != 2 || !item.has("seriesKey") || !item.has("tagpath")
                || !item.get("seriesKey").isJsonPrimitive() || !item.get("tagpath").isJsonPrimitive()) {
                throw new BadRequest("each path must contain only seriesKey and tagpath");
            }
            String key = item.get("seriesKey").getAsString();
            String tagpath = item.get("tagpath").getAsString();
            if (key.isBlank() || tagpath.isBlank()) {
                throw new BadRequest("seriesKey and tagpath must be non-empty strings");
            }
            if (!keys.add(key)) {
                throw new BadRequest("seriesKey values must be unique");
            }
            requested.add(new RequestedPath(key, tagpath));
        }
        long start = integer(payload, "start");
        long end = integer(payload, "end");
        long window;
        try {
            window = Math.subtractExact(end, start);
        } catch (ArithmeticException error) {
            throw new BadRequest("interval must be non-empty and no longer than 86400000 ms");
        }
        if (window <= 0 || window > MAX_WINDOW_MS) {
            throw new BadRequest("interval must be non-empty and no longer than 86400000 ms");
        }
        return new Request(List.copyOf(requested), start, end);
    }

    static List<QualifiedPath> resolve(Request request, Browser browser) {
        return resolve(request, browser, Clock.systemUTC());
    }

    static List<QualifiedPath> resolve(Request request, Browser browser, Clock clock) {
        Set<String> providers = new HashSet<>();
        for (RequestedPath item : request.paths()) {
            if (!item.tagpath().startsWith("histprov:")) {
                providers.add(shortProvider(item.tagpath()));
            }
        }
        Map<String, String> routes = resolveRoutes(providers, browser, clock.millis());
        List<QualifiedPath> resolved = new ArrayList<>();
        for (RequestedPath item : request.paths()) {
            String path = item.tagpath();
            if (!path.startsWith("histprov:")) {
                int close = path.indexOf(']');
                String provider = path.substring(1, close);
                String relative = path.substring(close + 1).replaceFirst("^/+", "");
                String route = routes.get(provider);
                if (route == null || route.isEmpty()) {
                    throw new BadRequest("No unique historical driver route for tag provider " + provider);
                }
                path = route + ":/tag:" + relative;
            }
            validateHistoricalPath(path);
            resolved.add(QualifiedPath.parseSafe(path));
        }
        return List.copyOf(resolved);
    }

    private static String shortProvider(String path) {
        int close = path.indexOf(']');
        if (!path.startsWith("[") || close < 2 || close == path.length() - 1
            || path.substring(close + 1).replaceFirst("^/+", "").isEmpty()) {
            throw new BadRequest("tagpath must include a provider and relative path");
        }
        return path.substring(1, close);
    }

    private static synchronized Map<String, String> resolveRoutes(Set<String> providers, Browser browser, long now) {
        Map<String, String> routes = new HashMap<>();
        Set<String> missing = new HashSet<>();
        for (String provider : providers) {
            CachedRoute cached = ROUTE_CACHE.get(provider);
            if (cached != null && now - cached.createdAt() < ROUTE_CACHE_TTL_MS) {
                routes.put(provider, cached.path());
            } else {
                ROUTE_CACHE.remove(provider);
                missing.add(provider);
            }
        }
        if (missing.isEmpty()) return routes;

        List<String> candidates = new ArrayList<>();
        BrowseFilter filter = new BrowseFilter().setRecursive(false);
        Iterable<String> providerRoots;
        try {
            providerRoots = browser.browse(new QualifiedPath(), filter);
        } catch (RuntimeException exception) {
            providerRoots = List.of();
        }
        for (String providerRoot : providerRoots) {
            if (!providerRoot.startsWith("histprov:")) continue;
            Iterable<String> driverRoots;
            try {
                driverRoots = browser.browse(QualifiedPath.parseSafe(providerRoot), filter);
            } catch (RuntimeException exception) {
                continue;
            }
            for (String path : driverRoots) {
                if (path.contains(":/drv:") && !path.contains(":/tag:")) {
                    candidates.add(path.replaceAll("/+$", ""));
                }
            }
        }
        for (String provider : missing) {
            String suffix = ":" + provider;
            List<String> matches = candidates.stream()
                .filter(path -> path.substring(path.indexOf(":/drv:") + 6).endsWith(suffix)).toList();
            if (matches.size() != 1) {
                throw new BadRequest("No unique historical driver route for tag provider " + provider);
            }
            while (ROUTE_CACHE.size() >= ROUTE_CACHE_MAX) {
                ROUTE_CACHE.remove(ROUTE_CACHE.keySet().iterator().next());
            }
            ROUTE_CACHE.put(provider, new CachedRoute(now, matches.get(0)));
            routes.put(provider, matches.get(0));
        }
        return routes;
    }

    private static void validateHistoricalPath(String path) {
        int providerEnd = path.indexOf(":/");
        int tag = path.indexOf(":/tag:");
        if (!path.startsWith("histprov:") || providerEnd <= "histprov:".length()
            || tag < 0 || tag + 6 >= path.length()) {
            throw new BadRequest("tagpath must be a valid historical tag path");
        }
    }

    static synchronized void clearRouteCache() {
        ROUTE_CACHE.clear();
    }

    static BasicTagHistoryQueryParams queryParams(Request request, List<? extends Path> paths) {
        BasicTagHistoryQueryParams params = new BasicTagHistoryQueryParams();
        params.setPaths(paths);
        params.setAliases(request.paths().stream().map(RequestedPath::seriesKey).toList());
        params.setStartDate(new Date(request.start()));
        params.setEndDate(new Date(request.end()));
        params.setReturnSize(-1);
        params.setReturnFormat(ReturnFormat.Tall);
        params.setQueryFlags(Flags.of(TagHistoryQueryFlags.NO_INTERPOLATION, TagHistoryQueryFlags.BOUNDING_VALUES_NO));
        return params;
    }

    static void stream(Request request, Browser browser, Query query, OutputStream output, Clock clock) {
        query.query(queryParams(request, resolve(request, browser)), new Writer(request, output, clock));
    }

    static final class Writer implements StreamingDatasetWriter {
        private final Request request;
        private final OutputStream output;
        private final Clock clock;
        private final long started;
        private final List<JsonArray> columns = List.of(new JsonArray(), new JsonArray(), new JsonArray(), new JsonArray(), new JsonArray(), new JsonArray());
        private String[] schema;
        private int timestampIndex;
        private int valueIndex;
        private int qualityIndex;
        private int pathIndex;
        private int rows;
        private int blockBytesEstimate = 256;
        private int blockCount;
        private long pointCount;
        private long bytes;
        private boolean terminal;

        Writer(Request request, OutputStream output, Clock clock) {
            this.request = request;
            this.output = output;
            this.clock = clock;
            started = clock.millis();
        }

        @Override
        public void initialize(String[] columnNames, Class<?>[] columnTypes, boolean qualityData, int rowCount) {
            schema = columnNames.clone();
            timestampIndex = column(columnNames, "timestamp");
            valueIndex = column(columnNames, "value");
            qualityIndex = column(columnNames, "quality");
            pathIndex = column(columnNames, "path");
            JsonObject header = new JsonObject();
            header.addProperty("type", "header");
            header.addProperty("protocolVersion", 1);
            header.addProperty("start", request.start());
            header.addProperty("end", request.end());
            JsonArray paths = new JsonArray();
            request.paths().forEach(path -> {
                JsonObject item = new JsonObject();
                item.addProperty("seriesKey", path.seriesKey());
                item.addProperty("tagpath", path.tagpath());
                paths.add(item);
            });
            header.add("paths", paths);
            emit(header);
        }

        @Override
        public void write(Object[] row, QualityCode[] qualities) throws IOException {
            checkActive();
            long timestamp = timestamp(row[timestampIndex]);
            if (timestamp < request.start() || timestamp >= request.end()) {
                return;
            }
            String seriesKey = String.valueOf(row[pathIndex]);
            RequestedPath requested = request.paths().stream().filter(path -> path.seriesKey().equals(seriesKey)).findFirst()
                .orElseThrow(() -> new IOException("historian returned an unknown Tall path identity"));
            Object value = row[valueIndex];
            Object quality = qualityIndex >= 0 ? row[qualityIndex]
                : qualities != null && valueIndex < qualities.length ? qualities[valueIndex] : null;
            JsonElement[] encoded = {
                new JsonPrimitive(seriesKey),
                new JsonPrimitive(requested.tagpath()),
                new JsonPrimitive(timestamp),
                json(value),
                quality == null ? JsonNull.INSTANCE : new JsonPrimitive(String.valueOf(quality)),
                new JsonPrimitive(valueType(value)),
            };
            int rowBytes = 32;
            for (JsonElement item : encoded) {
                rowBytes += item.toString().getBytes(StandardCharsets.UTF_8).length;
            }
            if (rows > 0 && blockBytesEstimate + rowBytes > MAX_BLOCK_BYTES) {
                flushBlock();
            }
            if (blockBytesEstimate + rowBytes > MAX_BLOCK_BYTES) {
                throw new StreamLimit("single historian row exceeds 1 MiB block limit");
            }
            for (int index = 0; index < encoded.length; index++) {
                columns.get(index).add(encoded[index]);
            }
            rows++;
            blockBytesEstimate += rowBytes;
            if (rows >= MAX_BLOCK_ROWS) {
                flushBlock();
            }
        }

        @Override
        public void finish() {
            if (terminal) {
                return;
            }
            try {
                flushBlock();
                terminal(true, null, null, false);
            } catch (RuntimeException exception) {
                emitFailureTerminal("HISTORIAN_STREAM_LIMIT", exception.getMessage(), false);
            }
        }

        @Override
        public void finishWithError(Exception error) {
            if (!terminal) {
                try {
                    flushBlock();
                    terminal(false, "HISTORIAN_QUERY_FAILED",
                        error == null || error.getMessage() == null ? "historian query failed" : error.getMessage(), false);
                } catch (RuntimeException exception) {
                    emitFailureTerminal("HISTORIAN_STREAM_LIMIT", exception.getMessage(), false);
                }
            }
        }

        private void emitFailureTerminal(String code, String message, boolean transientFailure) {
            if (terminal) {
                return;
            }
            try {
                terminal(false, code, message == null ? "historian stream failed" : message, transientFailure);
            } catch (RuntimeException ignored) {
                terminal = true;
            }
        }

        private void flushBlock() {
            if (rows == 0) {
                return;
            }
            int emittedRows = rows;
            JsonObject value = block();
            value.addProperty("sequence", blockCount);
            if (value.toString().getBytes(StandardCharsets.UTF_8).length > MAX_BLOCK_BYTES) {
                throw new StreamLimit("block exceeds 1 MiB limit");
            }
            emit(value);
            blockCount++;
            pointCount += emittedRows;
            clearBlock();
        }

        private void clearBlock() {
            for (JsonArray column : columns) {
                while (column.size() > 0) {
                    column.remove(column.size() - 1);
                }
            }
            rows = 0;
            blockBytesEstimate = 256;
        }

        private JsonObject block() {
            JsonObject block = new JsonObject();
            block.addProperty("type", "block");
            block.addProperty("rowCount", rows);
            JsonObject data = new JsonObject();
            String[] names = {"seriesKey", "tagpath", "timestamp", "value", "quality", "valueType"};
            for (int index = 0; index < names.length; index++) {
                data.add(names[index], columns.get(index));
            }
            block.add("columns", data);
            return block;
        }

        private void terminal(boolean ok, String code, String message, boolean transientFailure) {
            JsonObject value = new JsonObject();
            value.addProperty("type", "terminal");
            value.addProperty("sequence", blockCount);
            value.addProperty("ok", ok);
            value.addProperty("blockCount", blockCount);
            value.addProperty("pointCount", pointCount);
            if (!ok) {
                value.addProperty("code", code);
                value.addProperty("error", message);
                value.addProperty("transient", transientFailure);
            }
            emit(value, MAX_RESPONSE_BYTES);
            terminal = true;
        }

        private void emit(JsonObject value) {
            emit(value, MAX_RESPONSE_BYTES - TERMINAL_RESERVE_BYTES);
        }

        private void emit(JsonObject value, long limit) {
            if (limit == MAX_RESPONSE_BYTES) {
                if (terminal) throw new StreamLimit("stream is terminal");
            } else {
                checkActive();
            }
            byte[] line = (value + "\n").getBytes(StandardCharsets.UTF_8);
            if (bytes + line.length > limit) {
                throw new StreamLimit("response exceeds 64 MiB limit");
            }
            try {
                output.write(line);
                output.flush();
                bytes += line.length;
            } catch (IOException exception) {
                terminal = true;
                throw new StreamLimit("client disconnected", exception);
            }
        }

        private void checkActive() {
            if (terminal) {
                throw new StreamLimit("stream is terminal");
            }
            if (clock.millis() - started > MAX_DURATION_MS) {
                throw new StreamLimit("stream exceeds 120 second limit");
            }
        }

        private static int column(String[] names, String expected) {
            for (int index = 0; index < names.length; index++) {
                if (expected.equalsIgnoreCase(names[index])) {
                    return index;
                }
            }
            if ("quality".equals(expected)) {
                return -1;
            }
            throw new StreamLimit("historian returned an unsupported Tall dataset shape: " + String.join(",", names));
        }

        private static long timestamp(Object value) throws IOException {
            if (value instanceof Date date) {
                return date.getTime();
            }
            if (value instanceof Number number) {
                return number.longValue();
            }
            throw new IOException("historian timestamp is not a date or integer");
        }
    }

    static JsonElement json(Object value) {
        if (value == null) return JsonNull.INSTANCE;
        if (value instanceof Boolean booleanValue) return new JsonPrimitive(booleanValue);
        if (value instanceof Number number) return new JsonPrimitive(number);
        if (value instanceof Character character) return new JsonPrimitive(character);
        return new JsonPrimitive(String.valueOf(value));
    }

    static String valueType(Object value) {
        if (value == null) return "null";
        if (value instanceof Boolean) return "boolean";
        if (value instanceof Number) return "number";
        return "string";
    }

    private static long integer(JsonObject payload, String name) {
        try {
            JsonPrimitive value = payload.getAsJsonPrimitive(name);
            String text = value.getAsString();
            long parsed = Long.parseLong(text);
            if (!text.equals(Long.toString(parsed))) throw new NumberFormatException();
            return parsed;
        } catch (Exception exception) {
            throw new BadRequest("start and end must be integers");
        }
    }

    record RequestedPath(String seriesKey, String tagpath) {
    }

    record Request(List<RequestedPath> paths, long start, long end) {
    }

    private record CachedRoute(long createdAt, String path) {
    }

    interface Browser {
        Iterable<String> browse(QualifiedPath root, BrowseFilter filter);
    }

    interface Query {
        void query(BasicTagHistoryQueryParams params, StreamingDatasetWriter writer);
    }

    static final class BadRequest extends IllegalArgumentException {
        BadRequest(String message) { super(message); }
    }

    static final class StreamLimit extends RuntimeException {
        StreamLimit(String message) { super(message); }
        StreamLimit(String message, Throwable cause) { super(message, cause); }
    }
}
