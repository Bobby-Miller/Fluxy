/*
 * SPDX-FileCopyrightText: 2026 Green Pipe Partners, LLC
 * SPDX-License-Identifier: MPL-2.0
 */
package com.greenpipepartners.fluxy.gateway;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.io.InputStream;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Date;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import org.junit.jupiter.api.Test;

import com.inductiveautomation.ignition.common.gson.JsonObject;
import com.inductiveautomation.ignition.common.gson.JsonParser;
import com.inductiveautomation.ignition.common.sqltags.history.TagHistoryQueryFlags;

class HistorianStreamTest {
    private static final String REQUEST = "{\"paths\":[{\"seriesKey\":\"a\",\"tagpath\":\"histprov:main:/drv:x:default:/tag:t\"}],\"start\":1000,\"end\":2000}";

    @Test
    void sharedColumnarFixtureMatchesNativeProtocolShape() throws Exception {
        try (InputStream input = getClass().getResourceAsStream("/historian-columnar.ndjson")) {
            assertTrue(input != null);
            String[] lines = new String(input.readAllBytes(), StandardCharsets.UTF_8).trim().split("\\n");
            assertEquals("header", json(lines[0]).get("type").getAsString());
            JsonObject block = json(lines[1]);
            assertEquals(2, block.get("rowCount").getAsInt());
            assertEquals(2, block.getAsJsonObject("columns").getAsJsonArray("value").size());
            assertEquals(2, json(lines[2]).get("pointCount").getAsInt());
        }
    }

    @Test
    void validatesStrictParamsAndBuildsRawTallQuery() {
        HistorianStream.Request request = HistorianStream.parse(REQUEST);
        var params = HistorianStream.queryParams(request, java.util.List.of(
            com.inductiveautomation.ignition.common.QualifiedPath.parseSafe(request.paths().get(0).tagpath())
        ));
        assertEquals(-1, params.getReturnSize());
        assertEquals("Tall", params.getReturnFormat().name());
        assertTrue(params.getQueryFlags().hasFlag(TagHistoryQueryFlags.NO_INTERPOLATION));
        assertTrue(params.getQueryFlags().hasFlag(TagHistoryQueryFlags.BOUNDING_VALUES_NO));
        assertFalse(params.getQueryFlags().hasFlag(TagHistoryQueryFlags.IGNORE_BAD_QUALITY));
        assertThrows(HistorianStream.BadRequest.class, () -> HistorianStream.parse(REQUEST.replace("2000", "86402001")));
        assertThrows(HistorianStream.BadRequest.class, () -> HistorianStream.parse(
            REQUEST.replace("\"start\":1000,\"end\":2000", "\"start\":-9223372036854775808,\"end\":9223372036854775807")));
        assertThrows(HistorianStream.BadRequest.class, () -> HistorianStream.parse(REQUEST.replace("\"end\":2000", "\"end\":2000,\"limit\":1")));
    }

    @Test
    void resolvesShortPathsWithTwoLevelBrowseAndCachesRoute() {
        HistorianStream.clearRouteCache();
        AtomicInteger browses = new AtomicInteger();
        HistorianStream.Browser browser = (root, filter) -> {
            browses.incrementAndGet();
            assertFalse(filter.isRecursive());
            if (root.toString().isEmpty()) return List.of("histprov:main:/", "not-history");
            assertEquals("histprov:main", root.toString());
            return List.of("histprov:main:/drv:gateway:tag_04", "histprov:main:/drv:ignored:other");
        };
        HistorianStream.Request request = shortRequest("[tag_04]folder/tag");
        Clock initial = Clock.fixed(Instant.ofEpochMilli(1_000), ZoneOffset.UTC);

        assertEquals("histprov:main:/drv:gateway:tag_04:/tag:folder/tag",
            HistorianStream.resolve(request, browser, initial).get(0).toString());
        assertEquals(2, browses.get());
        HistorianStream.resolve(request, browser, Clock.fixed(Instant.ofEpochMilli(60_999), ZoneOffset.UTC));
        assertEquals(2, browses.get());
        HistorianStream.resolve(request, browser, Clock.fixed(Instant.ofEpochMilli(61_000), ZoneOffset.UTC));
        assertEquals(4, browses.get());
    }

    @Test
    void rejectsMissingAndAmbiguousDriverRoutes() {
        HistorianStream.Request request = shortRequest("[tag_04]tag");
        HistorianStream.Browser missing = twoLevel(List.of("histprov:main:/drv:gateway:other"));
        HistorianStream.clearRouteCache();
        assertThrows(HistorianStream.BadRequest.class, () -> HistorianStream.resolve(request, missing));

        HistorianStream.Browser ambiguous = twoLevel(List.of(
            "histprov:main:/drv:a:tag_04", "histprov:main:/drv:b:tag_04"));
        HistorianStream.clearRouteCache();
        assertThrows(HistorianStream.BadRequest.class, () -> HistorianStream.resolve(request, ambiguous));
    }

    @Test
    void rejectsMalformedResolvedPaths() {
        HistorianStream.clearRouteCache();
        assertThrows(HistorianStream.BadRequest.class,
            () -> HistorianStream.resolve(shortRequest("[tag_04]/"), twoLevel(List.of())));
        assertThrows(HistorianStream.BadRequest.class,
            () -> HistorianStream.resolve(shortRequest("histprov:main:/drv:x:default"), twoLevel(List.of())));
    }

    @Test
    void mapsTallSchemaFiltersEndAndRetainsBadQuality() throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        HistorianStream.Writer writer = writer(output);
        writer.initialize(new String[]{"Path", "Value", "Timestamp", "Quality"},
            new Class<?>[]{String.class, Object.class, Date.class, Object.class}, false, -1);
        writer.write(new Object[]{"a", 3.5, new Date(1500), "Bad_Stale"}, null);
        writer.write(new Object[]{"a", 4, new Date(2000), "Good"}, null);
        writer.finish();
        String[] lines = output.toString(StandardCharsets.UTF_8).split("\n");
        assertEquals("header", json(lines[0]).get("type").getAsString());
        JsonObject block = json(lines[1]);
        assertEquals(0, block.get("sequence").getAsInt());
        assertEquals(1, block.get("rowCount").getAsInt());
        assertEquals("Bad_Stale", block.getAsJsonObject("columns").getAsJsonArray("quality").get(0).getAsString());
        assertEquals("number", block.getAsJsonObject("columns").getAsJsonArray("valueType").get(0).getAsString());
        JsonObject terminal = json(lines[2]);
        assertTrue(terminal.get("ok").getAsBoolean());
        assertEquals(1, terminal.get("sequence").getAsInt());
        assertEquals(1, terminal.get("blockCount").getAsInt());
        assertEquals(1, terminal.get("pointCount").getAsInt());
    }

    @Test
    void blocksAtFiveThousandRowsAndOnlyEmitsOneTerminal() throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        HistorianStream.Writer writer = writer(output);
        writer.initialize(new String[]{"timestamp", "value", "quality", "path"}, new Class<?>[4], false, -1);
        for (int index = 0; index < 5001; index++) {
            writer.write(new Object[]{1000L, index, "Good", "a"}, null);
        }
        writer.finish();
        writer.finishWithError(new Exception("late"));
        String text = output.toString(StandardCharsets.UTF_8);
        assertTrue(text.contains("\"rowCount\":5000"));
        assertTrue(text.contains("\"rowCount\":1"));
        assertTrue(text.contains("\"blockCount\":2"));
        assertTrue(text.contains("\"pointCount\":5001"));
        assertEquals(1, text.split("\"type\":\"terminal\"", -1).length - 1);
    }

    @Test
    void splitsBeforeOneMiBAndRejectsAnOversizeSingleRow() throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        HistorianStream.Writer writer = writer(output);
        writer.initialize(new String[]{"timestamp", "value", "quality", "path"}, new Class<?>[4], false, -1);
        String halfMiB = "x".repeat(530_000);
        writer.write(new Object[]{1000L, halfMiB, "Good", "a"}, null);
        writer.write(new Object[]{1001L, halfMiB, "Good", "a"}, null);
        writer.finish();
        String text = output.toString(StandardCharsets.UTF_8);
        assertEquals(2, text.split("\"type\":\"block\"", -1).length - 1);

        HistorianStream.Writer oversize = writer(new ByteArrayOutputStream());
        oversize.initialize(new String[]{"timestamp", "value", "quality", "path"}, new Class<?>[4], false, -1);
        assertThrows(HistorianStream.StreamLimit.class,
            () -> oversize.write(new Object[]{1000L, "x".repeat(1_048_576), "Good", "a"}, null));
    }

    @Test
    void disconnectStopsWithoutAppendingTerminal() {
        OutputStream disconnected = new OutputStream() {
            @Override public void write(int value) throws IOException { throw new IOException("gone"); }
        };
        HistorianStream.Writer writer = writer(disconnected);
        assertThrows(HistorianStream.StreamLimit.class, () -> writer.initialize(
            new String[]{"timestamp", "value", "quality", "path"}, new Class<?>[4], false, -1));
        writer.finishWithError(new Exception("ignored"));
    }

    @Test
    void finishWithErrorProducesTerminalErrorAfterHeader() {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        HistorianStream.Writer writer = writer(output);
        writer.initialize(new String[]{"timestamp", "value", "quality", "path"}, new Class<?>[4], false, -1);
        writer.finishWithError(new Exception("backend failed"));
        String text = output.toString(StandardCharsets.UTF_8);
        assertTrue(text.contains("\"ok\":false"));
        assertTrue(text.contains("\"code\":\"HISTORIAN_QUERY_FAILED\""));
        assertTrue(text.contains("\"transient\":false"));
        assertTrue(text.contains("backend failed"));
    }

    private static HistorianStream.Writer writer(OutputStream output) {
        return new HistorianStream.Writer(HistorianStream.parse(REQUEST), output,
            Clock.fixed(Instant.ofEpochMilli(0), ZoneOffset.UTC));
    }

    private static HistorianStream.Request shortRequest(String path) {
        return HistorianStream.parse(REQUEST.replace("histprov:main:/drv:x:default:/tag:t", path));
    }

    private static HistorianStream.Browser twoLevel(List<String> drivers) {
        return (root, filter) -> root.toString().isEmpty() ? List.of("histprov:main:/") : drivers;
    }

    private static JsonObject json(String value) {
        return JsonParser.parseString(value).getAsJsonObject();
    }
}
