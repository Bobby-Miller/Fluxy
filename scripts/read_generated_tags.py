#!/usr/bin/env python3
"""Read generated tag paths through a live Fluxy bridge."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import fluxy
from fluxy import FluxyError


DEFAULT_TAG_PATHS_FILE = Path(__file__).resolve().parents[2] / "dev_tag_builder" / "out" / "tag_paths.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("FLUXY_BASE_URL"), required=not os.getenv("FLUXY_BASE_URL"))
    parser.add_argument("--token", default=os.getenv("FLUXY_TOKEN"))
    parser.add_argument("--tag-paths-file", type=Path, default=Path(os.getenv("FLUXY_TAG_PATHS_FILE", str(DEFAULT_TAG_PATHS_FILE))))
    parser.add_argument("--sample-size", type=int, default=int(os.getenv("FLUXY_SAMPLE_SIZE", "3")))
    parser.add_argument("--timeout-ms", type=int, default=int(os.getenv("FLUXY_TIMEOUT_MS", "45000")))
    return parser.parse_args()


def load_tag_paths(path: Path, sample_size: int) -> list[str]:
    tag_paths = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tag_paths.append(line)
        if len(tag_paths) >= sample_size:
            break
    return tag_paths


def main() -> int:
    args = parse_args()
    tag_paths = load_tag_paths(args.tag_paths_file, args.sample_size)
    if not tag_paths:
        print("No tag paths loaded from %s" % args.tag_paths_file, file=sys.stderr)
        return 2

    print("Generated tag read probe")
    print("base_url: %s" % args.base_url)
    print("token_configured: %s" % bool(args.token))
    print("tag_paths_file: %s" % args.tag_paths_file)
    print("sample_size: %s" % len(tag_paths))
    print("timeout_ms: %s" % args.timeout_ms)
    print("sampled_paths:")
    for tag_path in tag_paths:
        print("  %s" % tag_path)

    fx = fluxy.Fluxy(base_url=args.base_url, token=args.token)
    started = time.time()
    try:
        values = fx.tag.read_blocking(tag_paths, timeout=args.timeout_ms)
    except FluxyError as exc:
        print("Fluxy read failed: %s" % exc, file=sys.stderr)
        return 1

    elapsed = time.time() - started
    print("\nreturned_values: %s" % len(values))
    print("elapsed_seconds: %.3f" % elapsed)

    bad_count = 0
    for tag_path, value in zip(tag_paths, values, strict=True):
        print(
            "%s | quality=%s | value=%r | timestamp=%s"
            % (tag_path, value.quality, value.value, value.timestamp)
        )
        if not value.quality.startswith("Good"):
            bad_count += 1

    if len(values) != len(tag_paths):
        print("Count mismatch: requested=%s returned=%s" % (len(tag_paths), len(values)), file=sys.stderr)
        return 1
    if bad_count:
        print("Bad quality count: %s" % bad_count, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
