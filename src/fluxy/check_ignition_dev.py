from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from dataclasses import dataclass
from enum import Enum

import httpx


DEFAULT_GATEWAY_URL = "http://localhost:8088"
DEFAULT_FLUXY_BASE_URL = "http://localhost:8088/system/webdev/flux"
MANUAL_ATTENTION_TERMS = (
    "trial expired",
    "trial has expired",
    "trial period has expired",
    "license expired",
    "license has expired",
    "gateway trial",
    "restart trial",
    "reset trial",
    "commissioning",
)


class CheckState(Enum):
    OK = "ok"
    WARNING = "warning"
    FAIL = "fail"


@dataclass(frozen=True)
class CheckResult:
    name: str
    state: CheckState
    message: str
    manual_url: str | None = None


@dataclass(frozen=True)
class DevHealthReport:
    gateway: CheckResult
    fluxy: CheckResult

    @property
    def exit_code(self) -> int:
        states = {self.gateway.state, self.fluxy.state}
        if CheckState.FAIL in states:
            return 2
        if CheckState.WARNING in states:
            return 1
        return 0

    @property
    def manual_urls(self) -> list[str]:
        return [result.manual_url for result in (self.gateway, self.fluxy) if result.manual_url]


def body_needs_manual_attention(body: str) -> bool:
    normalized = body.lower()
    return any(term in normalized for term in MANUAL_ATTENTION_TERMS)


def gateway_home_url(gateway_url: str) -> str:
    return gateway_url.rstrip("/") + "/web/home"


def check_gateway(client: httpx.Client, gateway_url: str) -> CheckResult:
    manual_url = gateway_home_url(gateway_url)
    try:
        response = client.get(gateway_url, follow_redirects=True)
    except httpx.RequestError as exc:
        return CheckResult(
            name="Gateway",
            state=CheckState.FAIL,
            message="Gateway is unreachable: %s" % exc,
            manual_url=manual_url,
        )

    if body_needs_manual_attention(response.text):
        return CheckResult(
            name="Gateway",
            state=CheckState.WARNING,
            message="Gateway is reachable but appears to need manual trial/license attention.",
            manual_url=manual_url,
        )

    if response.status_code >= 500:
        return CheckResult(
            name="Gateway",
            state=CheckState.FAIL,
            message="Gateway returned HTTP %s." % response.status_code,
            manual_url=manual_url,
        )

    return CheckResult(
        name="Gateway",
        state=CheckState.OK,
        message="Gateway is reachable at %s." % str(response.url),
    )


def check_fluxy_bridge(client: httpx.Client, base_url: str, token: str | None) -> CheckResult:
    url = base_url.rstrip("/") + "/fluxy/util/getVersion"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer %s" % token

    try:
        response = client.post(url, json={}, headers=headers)
    except httpx.RequestError as exc:
        return CheckResult(
            name="Fluxy WebDev",
            state=CheckState.FAIL,
            message="Fluxy WebDev is unreachable: %s" % exc,
            manual_url=base_url,
        )

    if body_needs_manual_attention(response.text):
        return CheckResult(
            name="Fluxy WebDev",
            state=CheckState.WARNING,
            message="Fluxy bridge response suggests the gateway needs manual trial/license attention.",
            manual_url=base_url,
        )

    if response.status_code in {401, 403}:
        return CheckResult(
            name="Fluxy WebDev",
            state=CheckState.FAIL,
            message="Fluxy WebDev rejected the request with HTTP %s. Check FLUXY_TOKEN." % response.status_code,
            manual_url=base_url,
        )
    if response.status_code == 404:
        return CheckResult(
            name="Fluxy WebDev",
            state=CheckState.FAIL,
            message="Fluxy WebDev getVersion endpoint was not found. Deploy Fluxy WebDev resources.",
            manual_url=base_url,
        )
    if response.status_code >= 400:
        return CheckResult(
            name="Fluxy WebDev",
            state=CheckState.FAIL,
            message="Fluxy WebDev returned HTTP %s: %s" % (response.status_code, response.text[:160]),
            manual_url=base_url,
        )

    try:
        payload = response.json()
    except ValueError:
        return CheckResult(
            name="Fluxy WebDev",
            state=CheckState.FAIL,
            message="Fluxy WebDev returned non-JSON content.",
            manual_url=base_url,
        )

    version = str(payload.get("version") or "unknown") if isinstance(payload, dict) else "unknown"
    return CheckResult(
        name="Fluxy WebDev",
        state=CheckState.OK,
        message="Fluxy WebDev is reachable. Ignition version: %s." % version,
    )


def check_ignition_dev(
    *,
    gateway_url: str = DEFAULT_GATEWAY_URL,
    fluxy_base_url: str = DEFAULT_FLUXY_BASE_URL,
    token: str | None = None,
    timeout: float = 5.0,
    client: httpx.Client | None = None,
) -> DevHealthReport:
    owns_client = client is None
    selected_client = client or httpx.Client(timeout=timeout)
    try:
        return DevHealthReport(
            gateway=check_gateway(selected_client, gateway_url.rstrip("/")),
            fluxy=check_fluxy_bridge(selected_client, fluxy_base_url.rstrip("/"), token),
        )
    finally:
        if owns_client:
            selected_client.close()


def format_result(result: CheckResult) -> str:
    marker = {CheckState.OK: "OK", CheckState.WARNING: "ATTENTION", CheckState.FAIL: "FAIL"}[
        result.state
    ]
    line = "[%s] %s: %s" % (marker, result.name, result.message)
    if result.manual_url and result.state != CheckState.OK:
        line += "\n      Manual URL: %s" % result.manual_url
    return line


def format_report(report: DevHealthReport) -> str:
    lines = [format_result(report.gateway), format_result(report.fluxy)]
    if report.exit_code == 1:
        lines.append("Manual attention required before live Flux tests are expected to pass.")
    elif report.exit_code == 2:
        lines.append("Local Ignition development environment is not ready.")
    else:
        lines.append("Local Ignition development environment is ready.")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check local Ignition + Fluxy WebDev readiness for development tests."
    )
    parser.add_argument("--gateway-url", default=os.getenv("IGNITION_GATEWAY_URL", DEFAULT_GATEWAY_URL))
    parser.add_argument("--fluxy-base-url", default=os.getenv("FLUXY_BASE_URL", DEFAULT_FLUXY_BASE_URL))
    parser.add_argument("--token", default=os.getenv("FLUXY_TOKEN"))
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open manual-attention URLs in a browser when checks fail or need attention.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = check_ignition_dev(
        gateway_url=args.gateway_url,
        fluxy_base_url=args.fluxy_base_url,
        token=args.token,
        timeout=args.timeout,
    )
    print(format_report(report))
    if args.open:
        for url in report.manual_urls:
            webbrowser.open(url)
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
