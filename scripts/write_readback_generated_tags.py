#!/usr/bin/env python3
"""Write five generated memory tags and read them back."""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
from pathlib import Path

import fluxy
from fluxy import FluxyError


DEFAULT_TAG_PATHS_FILE = Path(__file__).resolve().parents[2] / "dev_tag_builder" / "out" / "tag_paths.txt"
DEFAULT_VALUES = [1.1, 2.2, 3.3, 4.4, 5.5]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("FLUXY_BASE_URL"), required=not os.getenv("FLUXY_BASE_URL"))
    parser.add_argument("--token", default=os.getenv("FLUXY_TOKEN"))
    parser.add_argument("--tag-paths-file", type=Path, default=Path(os.getenv("FLUXY_TAG_PATHS_FILE", str(DEFAULT_TAG_PATHS_FILE))))
    parser.add_argument("--timeout-ms", type=int, default=int(os.getenv("FLUXY_TIMEOUT_MS", "45000")))
    return parser.parse_args()


def load_tag_paths(path: Path, count: int) -> list[str]:
    tag_paths = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tag_paths.append(line)
        if len(tag_paths) >= count:
            break
    return tag_paths


def print_values(label: str, tag_paths: list[str], values) -> None:
    print("\n%s" % label)
    for tag_path, value in zip(tag_paths, values, strict=True):
        print(
            "%s | quality=%s | value=%r | timestamp=%s"
            % (tag_path, value.quality, value.value, value.timestamp)
        )


def main() -> int:
    args = parse_args()
    tag_paths = load_tag_paths(args.tag_paths_file, len(DEFAULT_VALUES))
    if len(tag_paths) != len(DEFAULT_VALUES):
        print("Expected %d tag paths, loaded %d" % (len(DEFAULT_VALUES), len(tag_paths)), file=sys.stderr)
        return 2

    print("Generated tag write/readback probe")
    print("base_url: %s" % args.base_url)
    print("token_configured: %s" % bool(args.token))
    print("tag_paths_file: %s" % args.tag_paths_file)
    print("timeout_ms: %s" % args.timeout_ms)
    print("write_values: %r" % DEFAULT_VALUES)
    print("tag_paths:")
    for tag_path in tag_paths:
        print("  %s" % tag_path)

    fx = fluxy.Fluxy(base_url=args.base_url, token=args.token)

    try:
        before = fx.tag.read_blocking(tag_paths, timeout=args.timeout_ms)
        print_values("before", tag_paths, before)

        started = time.time()
        write_results = fx.tag.write_blocking(tag_paths, DEFAULT_VALUES, timeout=args.timeout_ms)
        elapsed = time.time() - started
        print("\nwrite_results")
        print("elapsed_seconds: %.3f" % elapsed)
        for tag_path, result in zip(tag_paths, write_results, strict=True):
            print("%s | quality=%s" % (tag_path, result.quality))

        bad_writes = [result for result in write_results if not result.quality.startswith("Good")]
        if bad_writes:
            print("Bad write qualities: %r" % bad_writes, file=sys.stderr)
            return 1

        after = fx.tag.read_blocking(tag_paths, timeout=args.timeout_ms)
        print_values("after", tag_paths, after)
    except FluxyError as exc:
        print("Fluxy operation failed: %s" % exc, file=sys.stderr)
        return 1

    mismatches = []
    for tag_path, expected, actual in zip(tag_paths, DEFAULT_VALUES, after, strict=True):
        try:
            actual_float = float(actual.value)
        except (TypeError, ValueError):
            mismatches.append((tag_path, expected, actual.value, actual.quality))
            continue
        if not math.isclose(actual_float, expected, rel_tol=0.0, abs_tol=0.0001):
            mismatches.append((tag_path, expected, actual.value, actual.quality))

    if mismatches:
        print("Readback mismatches: %r" % mismatches, file=sys.stderr)
        return 1

    print("\nwrite/readback succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
