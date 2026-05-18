import httpx

from fluxy.check_ignition_dev import CheckState, check_ignition_dev, format_report


def test_check_ignition_dev_reports_ready_when_gateway_and_fluxy_are_healthy():
    def handler(request):
        if request.method == "GET" and request.url.path == "/":
            return httpx.Response(200, text="Ignition Gateway")
        if request.method == "POST" and request.url.path == "/system/webdev/flux/fluxy/util/getVersion":
            return httpx.Response(200, json={"ok": True, "version": "8.3.0"})
        return httpx.Response(404)

    report = check_ignition_dev(client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert report.exit_code == 0
    assert report.gateway.state is CheckState.OK
    assert report.fluxy.state is CheckState.OK
    assert "ready" in format_report(report)


def test_check_ignition_dev_detects_manual_trial_attention_from_gateway_body():
    def handler(request):
        if request.method == "GET" and request.url.path == "/":
            return httpx.Response(200, text="Your trial period has expired")
        if request.method == "POST" and request.url.path == "/system/webdev/flux/fluxy/util/getVersion":
            return httpx.Response(200, json={"ok": True, "version": "8.3.0"})
        return httpx.Response(404)

    report = check_ignition_dev(client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert report.exit_code == 1
    assert report.gateway.state is CheckState.WARNING
    assert report.gateway.manual_url == "http://localhost:8088/web/home"
    assert "manual trial/license attention" in report.gateway.message


def test_check_ignition_dev_reports_fluxy_auth_failure():
    def handler(request):
        if request.method == "GET" and request.url.path == "/":
            return httpx.Response(200, text="Ignition Gateway")
        if request.method == "POST" and request.url.path == "/system/webdev/flux/fluxy/util/getVersion":
            assert request.headers["authorization"] == "Bearer bad-token"
            return httpx.Response(403, text="Forbidden")
        return httpx.Response(404)

    report = check_ignition_dev(
        token="bad-token",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert report.exit_code == 2
    assert report.fluxy.state is CheckState.FAIL
    assert "Check FLUXY_TOKEN" in report.fluxy.message


def test_check_ignition_dev_reports_missing_fluxy_webdev_deployment():
    def handler(request):
        if request.method == "GET" and request.url.path == "/":
            return httpx.Response(200, text="Ignition Gateway")
        if request.method == "POST" and request.url.path == "/system/webdev/flux/fluxy/util/getVersion":
            return httpx.Response(404, text="Not found")
        return httpx.Response(404)

    report = check_ignition_dev(client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert report.exit_code == 2
    assert report.fluxy.state is CheckState.FAIL
    assert "Deploy Fluxy WebDev" in report.fluxy.message
