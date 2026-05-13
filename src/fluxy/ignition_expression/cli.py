from __future__ import annotations

import argparse
import json

from fluxy.ignition_expression.bindings import resolve_parameter_binding


def main() -> None:
    parser = argparse.ArgumentParser(description="Ignition expression utility commands.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve = subparsers.add_parser("resolve-binding", help="Resolve an Ignition parameter binding string")
    resolve.add_argument("template")
    resolve.add_argument("--context", required=True, help="JSON object of parameter values")

    args = parser.parse_args()
    if args.command == "resolve-binding":
        context = json.loads(args.context)
        result = resolve_parameter_binding(args.template, context)
        print(
            json.dumps(
                {
                    "resolved": result.resolved,
                    "value": result.value,
                    "resolvedTokens": result.resolved_tokens,
                    "unresolvedTokens": list(result.unresolved_tokens),
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
