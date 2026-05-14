from __future__ import annotations

import argparse
import dataclasses
import os
from pathlib import Path
from typing import Any

from fluxy import Fluxy


def create_server(
    fx: Fluxy,
    *,
    allow_writes: bool = False,
    allow_destructive: bool = False,
) -> Any:
    try:
        from mcp.server.fastmcp import FastMCP  # pyright: ignore[reportMissingImports]
    except ImportError as exc:
        raise SystemExit("MCP support requires `fluxy-ign[mcp]` or `uv sync --extra mcp`.") from exc

    server = FastMCP("fluxy")
    register_tools(server, fx, allow_writes=allow_writes, allow_destructive=allow_destructive)
    return server


def register_tools(
    server: Any,
    fx: Fluxy,
    *,
    allow_writes: bool = False,
    allow_destructive: bool = False,
) -> None:
    @server.tool()
    def fluxy_ping() -> dict[str, Any]:
        return {"ok": True, "base_url": fx.client.base_url}

    @server.tool()
    def ignition_get_version(refresh: bool = False) -> dict[str, Any]:
        return _to_wire(fx.util.get_version(refresh=refresh))

    @server.tool()
    def ignition_get_modules() -> list[dict[str, Any]]:
        return _to_wire(fx.util.get_modules())

    @server.tool()
    def project_get_project_name() -> str:
        return fx.project.get_project_name()

    @server.tool()
    def project_get_project_names() -> list[str]:
        return fx.project.get_project_names()

    @server.tool()
    def project_request_scan() -> dict[str, Any]:
        return _to_wire(fx.project.request_scan())

    @server.tool()
    def tag_read_blocking(tag_paths: str | list[str], timeout_ms: int | None = None) -> Any:
        return _to_wire(fx.tag.read_blocking(tag_paths, timeout=timeout_ms))

    @server.tool()
    def tag_browse(path: str | None = None, tag_filter: dict[str, Any] | None = None) -> Any:
        return _to_wire(fx.tag.browse(path, tag_filter=tag_filter))

    @server.tool()
    def tag_get_configuration(path: str, recursive: bool = False) -> list[dict[str, Any]]:
        return fx.tag.get_configuration(path, recursive=recursive)

    @server.tool()
    def opc_get_servers(include_disabled: bool = False) -> list[str]:
        return fx.opc.get_servers(include_disabled=include_disabled)

    @server.tool()
    def opc_get_server_state(opc_server: str) -> str | None:
        return fx.opc.get_server_state(opc_server)

    @server.tool()
    def opc_browse(
        opc_server: str | None = None,
        device: str | None = None,
        folder_path: str | None = None,
        opc_item_path: str | None = None,
    ) -> list[dict[str, Any]]:
        return fx.opc.browse(
            opc_server=opc_server,
            device=device,
            folder_path=folder_path,
            opc_item_path=opc_item_path,
        )

    @server.tool()
    def device_list_devices() -> list[dict[str, Any]]:
        return _to_wire(fx.device.list_devices())

    if allow_writes:

        @server.tool()
        def tag_write_blocking(
            tag_paths: str | list[str], values: Any | list[Any], timeout_ms: int | None = None
        ) -> Any:
            return _to_wire(fx.tag.write_blocking(tag_paths, values, timeout=timeout_ms))

        @server.tool()
        def tag_configure(
            tags: list[dict[str, Any]],
            base_path: str | None = None,
            collision_policy: str = "o",
        ) -> list[dict[str, Any]]:
            return _to_wire(fx.tag.configure(tags, base_path=base_path, collision_policy=collision_policy))

    if allow_destructive:

        @server.tool()
        def tag_delete_tags(tag_paths: str | list[str]) -> Any:
            return _to_wire(fx.tag.delete_tags(tag_paths))


def _to_wire(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {key: _to_wire(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _to_wire(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_wire(item) for item in value]
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an MCP server backed by a Fluxy Ignition bridge.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("FLUXY_BASE_URL", "http://localhost:8088/system/webdev/flux"),
    )
    parser.add_argument("--token", default=os.getenv("FLUXY_TOKEN"))
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--project-location", default=os.getenv("FLUXY_PROJECT_LOCATION"))
    parser.add_argument("--tag-provider", default=os.getenv("FLUXY_TAG_PROVIDER", "default"))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("FLUXY_TIMEOUT_SECONDS", "60")))
    parser.add_argument("--allow-writes", action="store_true")
    parser.add_argument("--allow-destructive", action="store_true")
    return parser.parse_args()


def selected_token(args: argparse.Namespace) -> str | None:
    if args.token and args.token_file:
        raise SystemExit("Use either --token or --token-file, not both.")
    if args.token_file:
        return args.token_file.read_text(encoding="utf-8").strip()
    return args.token


def main() -> None:
    args = parse_args()
    fx = Fluxy(
        base_url=args.base_url,
        token=selected_token(args),
        project_location=args.project_location,
        tag_provider=args.tag_provider,
        timeout=args.timeout,
    )
    server = create_server(
        fx,
        allow_writes=args.allow_writes,
        allow_destructive=args.allow_destructive,
    )
    server.run()


if __name__ == "__main__":
    main()
