from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


TOKEN_PATTERN = re.compile(r"\{([^{}]+)\}")
ARITHMETIC_TOKEN_PATTERN = re.compile(r"^([A-Za-z_][\w]*)\s*([+-])\s*(\d+(?:\.\d+)?)$")


@dataclass(frozen=True)
class BindingResolution:
    template: str
    value: str
    resolved_tokens: dict[str, Any]
    unresolved_tokens: tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return not self.unresolved_tokens


def resolve_parameter_binding(template: str, context: Mapping[str, Any]) -> BindingResolution:
    resolved_tokens: dict[str, Any] = {}
    unresolved_tokens: list[str] = []

    def replace(match: re.Match[str]) -> str:
        token = match.group(1).strip()
        if token not in context:
            arithmetic_value = resolve_arithmetic_token(token, context)
            if arithmetic_value is not None:
                resolved_tokens[token] = arithmetic_value
                return str(arithmetic_value)
            unresolved_tokens.append(token)
            return match.group(0)
        value = unwrap_parameter_value(context[token])
        if isinstance(value, dict) and value.get("bindType") == "parameter":
            nested = resolve_parameter_binding(str(value.get("binding") or ""), context)
            resolved_tokens.update(
                {f"{token}.{key}": item for key, item in nested.resolved_tokens.items()}
            )
            unresolved_tokens.extend(nested.unresolved_tokens)
            value = nested.value
        resolved_tokens[token] = value
        return "" if value is None else str(value)

    return BindingResolution(
        template=template,
        value=TOKEN_PATTERN.sub(replace, template),
        resolved_tokens=resolved_tokens,
        unresolved_tokens=tuple(dict.fromkeys(unresolved_tokens)),
    )


def unwrap_parameter_value(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def resolve_arithmetic_token(token: str, context: Mapping[str, Any]) -> str | None:
    match = ARITHMETIC_TOKEN_PATTERN.match(token)
    if match is None:
        return None

    name, operator, operand_text = match.groups()
    if name not in context:
        return None

    value = unwrap_parameter_value(context[name])
    try:
        base = float(value)
        operand = float(operand_text)
    except (TypeError, ValueError):
        return None

    result = base + operand if operator == "+" else base - operand
    return str(int(result)) if result.is_integer() else str(result)


def extract_binding_tokens(template: str) -> tuple[str, ...]:
    return tuple(match.group(1).strip() for match in TOKEN_PATTERN.finditer(template))
