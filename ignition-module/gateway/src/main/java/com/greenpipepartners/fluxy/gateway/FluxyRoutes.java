/*
 * SPDX-FileCopyrightText: 2026 Green Pipe Partners, LLC
 * SPDX-License-Identifier: MPL-2.0
 */
package com.greenpipepartners.fluxy.gateway;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Pattern;

import com.inductiveautomation.ignition.common.gson.JsonArray;
import com.inductiveautomation.ignition.common.gson.JsonElement;
import com.inductiveautomation.ignition.common.gson.JsonObject;
import com.inductiveautomation.ignition.common.gson.JsonParser;
import com.inductiveautomation.ignition.common.model.ApplicationScope;
import com.inductiveautomation.ignition.common.script.ScriptContext;
import com.inductiveautomation.ignition.common.script.ScriptManager;
import com.inductiveautomation.ignition.common.sqltags.model.types.DataQuality;
import com.inductiveautomation.ignition.common.util.LoggerEx;
import com.inductiveautomation.ignition.gateway.audit.AuditProfile;
import com.inductiveautomation.ignition.gateway.audit.AuditRecordBuilder;
import com.inductiveautomation.ignition.gateway.auth.apitoken.ApiTokenManager;
import com.inductiveautomation.ignition.gateway.dataroutes.AccessControlStrategy;
import com.inductiveautomation.ignition.gateway.dataroutes.HttpMethod;
import com.inductiveautomation.ignition.gateway.dataroutes.RequestContext;
import com.inductiveautomation.ignition.gateway.dataroutes.RouteGroup;
import com.inductiveautomation.ignition.gateway.model.GatewayContext;
import jakarta.servlet.http.HttpServletResponse;
import org.python.core.Py;
import org.python.core.PyObject;
import org.python.core.PyStringMap;

final class FluxyRoutes {
    private static final String MODULE_VERSION = "0.1.3 (b20260711)";
    private static final int MAX_BODY_CHARS = 1_048_576;
    private static final int MAX_TARGETS = 20;
    private static final int MAX_TARGET_LENGTH = 256;
    private static final Pattern TRACE_ID_PATTERN = Pattern.compile("[A-Za-z0-9._:-]{1,128}");
    private static final Set<String> READ_ROUTES = Set.of(
        "/capabilities",
        "/util/getVersion",
        "/util/queryAuditLog",
        "/tag/readBlocking",
        "/tag/browse",
        "/tag/getConfiguration",
        "/historian/browse",
        "/historian/page",
        "/historian/queryRawPoints"
    );
    private static final Set<String> WRITE_ROUTES = Set.of(
        "/tag/configure",
        "/tag/writeBlocking",
        "/tag/deleteTags",
        "/historian/storeDataPoints"
    );

    private final GatewayContext context;
    private final LoggerEx log;
    private final ModuleLicenseGate licenseGate;
    private final ScriptManager scriptManager;
    private final PyObject dispatchFunction;
    private final AtomicBoolean missingAuditProfileLogged = new AtomicBoolean();

    FluxyRoutes(GatewayContext context, LoggerEx log, ModuleLicenseGate licenseGate) {
        this.context = context;
        this.log = log;
        this.licenseGate = licenseGate;
        scriptManager = context.getScriptManager();
        dispatchFunction = loadDispatcher(scriptManager);
    }

    void mount(RouteGroup routes) {
        READ_ROUTES.forEach(path -> mount(routes, path, ApiTokenManager.TOKEN_READ));
        WRITE_ROUTES.forEach(path -> mount(routes, path, ApiTokenManager.TOKEN_WRITE));
        routes.newRoute("/historian/stream")
            .method(HttpMethod.POST)
            .acceptedTypes(RouteGroup.TYPE_JSON)
            .type("application/x-ndjson")
            .handler(this::handleHistorianStream)
            .renderer(Object::toString)
            .accessControl(ApiTokenManager.TOKEN_READ)
            .concurrency(2, 4)
            .nocache()
            .mount();
    }

    private String handleHistorianStream(RequestContext request, HttpServletResponse response) {
        ModuleLicenseGate.Decision decision = licenseGate.decision();
        if (!decision.permitted()) {
            response.setStatus(decision.status());
            response.setContentType(RouteGroup.TYPE_JSON);
            return licenseErrorJson(decision);
        }
        try {
            String body = request.readBody();
            if (body.length() > MAX_BODY_CHARS) {
                response.setStatus(HttpServletResponse.SC_REQUEST_ENTITY_TOO_LARGE);
                response.setContentType(RouteGroup.TYPE_JSON);
                return errorJson("Request body exceeds 1 MiB limit");
            }
            HistorianStream.Request streamRequest = HistorianStream.parse(body);
            var manager = context.getTagHistoryManager();
            var paths = HistorianStream.resolve(streamRequest, (root, filter) -> {
                var values = new java.util.ArrayList<String>();
                manager.browseHistoricalTags(root, filter).getResults()
                    .forEach(result -> values.add(result.getPath().toString()));
                return values;
            });
            response.setStatus(HttpServletResponse.SC_OK);
            response.setContentType("application/x-ndjson");
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            response.setHeader("Cache-Control", "no-store");
            var output = response.getOutputStream();
            var writer = new HistorianStream.Writer(streamRequest, output, java.time.Clock.systemUTC());
            try {
                manager.queryHistory(
                    HistorianStream.queryParams(streamRequest, paths),
                    writer
                );
            } catch (RuntimeException exception) {
                writer.finishWithError(exception);
            }
            return "";
        } catch (HistorianStream.BadRequest exception) {
            if (response.isCommitted()) return "";
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.setContentType(RouteGroup.TYPE_JSON);
            return errorJson(exception.getMessage());
        } catch (IOException exception) {
            if (response.isCommitted()) return "";
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            response.setContentType(RouteGroup.TYPE_JSON);
            return errorJson("Unable to read request body");
        }
    }

    private void mount(RouteGroup routes, String path, AccessControlStrategy accessControl) {
        routes.newRoute(path)
            .method(HttpMethod.POST)
            .acceptedTypes(RouteGroup.TYPE_JSON)
            .type(RouteGroup.TYPE_JSON)
            .handler((request, response) -> handle(path.substring(1), request, response))
            .renderer(Object::toString)
            .accessControl(accessControl)
            .concurrency(16, 64)
            .nocache()
            .mount();
    }

    private String handle(String operation, RequestContext request, HttpServletResponse response) {
        long started = System.nanoTime();
        TraceContext trace = traceContext(request);
        response.setHeader("X-Fluxy-Request-Id", trace.requestId());
        response.setHeader("X-Fluxy-Run-Id", trace.runId());
        ModuleLicenseGate.Decision licenseDecision = licenseGate.decision();
        if (!licenseDecision.permitted()) {
            response.setHeader("Cache-Control", "no-store");
            return complete(
                operation,
                request,
                response,
                trace,
                "{}",
                licenseDecision.status(),
                licenseErrorJson(licenseDecision),
                started
            );
        }
        String body = "{}";
        try {
            body = request.readBody();
            if (body.length() > MAX_BODY_CHARS) {
                return complete(
                    operation,
                    request,
                    response,
                    trace,
                    body,
                    HttpServletResponse.SC_REQUEST_ENTITY_TOO_LARGE,
                    errorJson("Request body exceeds 1 MiB limit"),
                    started
                );
            }
            if (body.isBlank()) {
                body = "{}";
            }

            PyObject result;
            try (var ignored = ScriptContext.push(builder -> builder
                .tagProvider("default")
                .description("Fluxy module: " + operation))) {
                result = scriptManager.runFunction(
                    dispatchFunction,
                    Py.newUnicode(operation),
                    Py.newUnicode(body)
                );
            }

            JsonObject envelope = JsonParser.parseString(result.asString()).getAsJsonObject();
            int status = envelope.get("status").getAsInt();
            JsonElement responseBody = envelope.get("body");
            return complete(
                operation,
                request,
                response,
                trace,
                body,
                status,
                responseBody.toString(),
                started
            );
        } catch (Exception exception) {
            log.error("Fluxy operation failed: " + operation, exception);
            return complete(
                operation,
                request,
                response,
                trace,
                body,
                HttpServletResponse.SC_INTERNAL_SERVER_ERROR,
                errorJson("Fluxy module failed to execute the request"),
                started
            );
        }
    }

    private String complete(
        String operation,
        RequestContext request,
        HttpServletResponse response,
        TraceContext trace,
        String requestBody,
        int status,
        String responseBody,
        long started
    ) {
        long durationMicros = (System.nanoTime() - started) / 1_000;
        boolean mutation = WRITE_ROUTES.contains("/" + operation);
        RequestSummary summary = summarize(operation, requestBody);
        response.setStatus(status);

        String message = String.format(
            "actor=%s operation=%s requestId=%s runId=%s script=%s status=%d durationMicros=%d targetCount=%d targets=%s",
            request.getActor(),
            operation,
            trace.requestId(),
            trace.runId(),
            trace.scriptName().isBlank() ? "-" : trace.scriptName(),
            status,
            durationMicros,
            summary.count(),
            summary.targets().isBlank() ? "-" : summary.targets()
        );
        if (status >= 400) {
            log.warn(message);
        } else if (mutation) {
            log.info(message);
        } else {
            log.debug(message);
        }

        if (mutation) {
            auditMutation(operation, request, trace, summary, status, durationMicros);
        }
        return responseBody;
    }

    private void auditMutation(
        String operation,
        RequestContext request,
        TraceContext trace,
        RequestSummary summary,
        int status,
        long durationMicros
    ) {
        try {
            AuditProfile profile = context.getAuditManager().getGatewayAuditProfile();
            if (profile == null) {
                if (missingAuditProfileLogged.compareAndSet(false, true)) {
                    log.warn("Fluxy mutation auditing is disabled because no Gateway audit profile is configured");
                }
                return;
            }

            JsonObject metadata = new JsonObject();
            metadata.addProperty("requestId", trace.requestId());
            metadata.addProperty("runId", trace.runId());
            if (!trace.scriptName().isBlank()) {
                metadata.addProperty("script", trace.scriptName());
            }
            metadata.addProperty("httpStatus", status);
            metadata.addProperty("durationMicros", durationMicros);
            metadata.addProperty("targetCount", summary.count());
            metadata.addProperty("contractVersion", 1);

            profile.audit(new AuditRecordBuilder()
                .setAction("Fluxy." + operation)
                .setActionTarget(summary.targets().isBlank() ? operation : summary.targets())
                .setActionValue(metadata.toString())
                .setActor(request.getActor())
                .setActorHost(request.getRequest().getRemoteAddr())
                .setOriginatingContext(ApplicationScope.GATEWAY)
                .setOriginatingSystem("Fluxy Module " + MODULE_VERSION)
                .setStatusCode(status < 400 ? DataQuality.GOOD_DATA.getIntValue() : 0)
                .setTimestamp(new Date())
                .build());
        } catch (Exception exception) {
            log.error("Unable to write Fluxy audit record for " + operation, exception);
        }
    }

    private static TraceContext traceContext(RequestContext request) {
        String requestId = validTraceId(request.getRequest().getHeader("X-Fluxy-Request-Id"));
        if (requestId.isBlank()) {
            requestId = UUID.randomUUID().toString();
        }
        String runId = validTraceId(request.getRequest().getHeader("X-Fluxy-Run-Id"));
        if (runId.isBlank()) {
            runId = requestId;
        }
        String scriptName = safeText(request.getRequest().getHeader("X-Fluxy-Script"), 128);
        return new TraceContext(requestId, runId, scriptName);
    }

    private static String validTraceId(String value) {
        if (value == null || !TRACE_ID_PATTERN.matcher(value).matches()) {
            return "";
        }
        return value;
    }

    private static RequestSummary summarize(String operation, String body) {
        List<String> targets = new ArrayList<>();
        try {
            JsonObject payload = JsonParser.parseString(body).getAsJsonObject();
            switch (operation) {
                case "tag/configure" -> {
                    String basePath = stringProperty(payload, "basePath");
                    JsonArray tags = payload.has("tags") && payload.get("tags").isJsonArray()
                        ? payload.getAsJsonArray("tags")
                        : new JsonArray();
                    for (JsonElement tag : tags) {
                        if (tag.isJsonObject()) {
                            String name = stringProperty(tag.getAsJsonObject(), "name");
                            addTarget(targets, joinTagPath(basePath, name));
                        }
                    }
                    if (targets.isEmpty()) {
                        addTarget(targets, basePath);
                    }
                }
                case "tag/writeBlocking", "tag/deleteTags" -> addArrayTargets(
                    targets,
                    payload,
                    "tagPaths"
                );
                case "historian/storeDataPoints" -> addArrayTargets(targets, payload, "paths");
                default -> {
                }
            }
        } catch (Exception ignored) {
            // Invalid bodies are handled by the dispatcher; logging must not change request behavior.
        }
        return new RequestSummary(String.join(";", targets), targets.size());
    }

    private static void addArrayTargets(List<String> targets, JsonObject payload, String key) {
        if (!payload.has(key) || !payload.get(key).isJsonArray()) {
            return;
        }
        for (JsonElement element : payload.getAsJsonArray(key)) {
            if (element.isJsonPrimitive() && element.getAsJsonPrimitive().isString()) {
                addTarget(targets, element.getAsString());
            }
        }
    }

    private static void addTarget(List<String> targets, String target) {
        if (targets.size() >= MAX_TARGETS || target == null || target.isBlank()) {
            return;
        }
        targets.add(safeText(target, MAX_TARGET_LENGTH));
    }

    private static String stringProperty(JsonObject object, String key) {
        if (!object.has(key) || !object.get(key).isJsonPrimitive()) {
            return "";
        }
        return object.get(key).getAsString();
    }

    private static String joinTagPath(String basePath, String name) {
        if (basePath == null || basePath.isBlank()) {
            return name;
        }
        if (name == null || name.isBlank()) {
            return basePath;
        }
        return basePath.endsWith("]") || basePath.endsWith("/")
            ? basePath + name
            : basePath + "/" + name;
    }

    private static String safeText(String value, int maxLength) {
        if (value == null) {
            return "";
        }
        String safe = value.replace('\r', ' ').replace('\n', ' ').trim();
        return safe.length() <= maxLength ? safe : safe.substring(0, maxLength);
    }

    private static PyObject loadDispatcher(ScriptManager scriptManager) {
        String source;
        try (InputStream stream = FluxyRoutes.class.getResourceAsStream("/fluxy_dispatch.py")) {
            if (stream == null) {
                throw new IllegalStateException("Missing fluxy_dispatch.py module resource");
            }
            source = new String(stream.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException exception) {
            throw new IllegalStateException("Unable to read Fluxy dispatcher", exception);
        }

        PyStringMap locals = scriptManager.createLocalsMap();
        try {
            scriptManager.runCode(source, locals, locals, "FluxyModule:fluxy_dispatch.py");
        } catch (Exception exception) {
            throw new IllegalStateException("Unable to compile Fluxy dispatcher", exception);
        }
        PyObject dispatcher = locals.__finditem__("dispatch");
        if (dispatcher == null || !dispatcher.isCallable()) {
            throw new IllegalStateException("Fluxy dispatcher resource did not define dispatch()");
        }
        return dispatcher;
    }

    private static String errorJson(String message) {
        JsonObject body = new JsonObject();
        body.addProperty("ok", false);
        body.addProperty("error", message);
        return body.toString();
    }

    private static String licenseErrorJson(ModuleLicenseGate.Decision decision) {
        JsonObject body = new JsonObject();
        body.addProperty("ok", false);
        body.addProperty("code", decision.code());
        body.addProperty("error", decision.message());
        return body.toString();
    }

    private record TraceContext(String requestId, String runId, String scriptName) {
    }

    private record RequestSummary(String targets, int count) {
    }
}
