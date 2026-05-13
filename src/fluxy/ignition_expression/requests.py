from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from fluxy.ignition_expression.bindings import BindingResolution, resolve_parameter_binding


IGNITION_PROVIDER_PREFIX = "["


@dataclass(frozen=True)
class TagRequest:
    tag_path: str
    value_source: str
    payload: str
    resolution: BindingResolution | None = None
    opc_server: str = ""
    data_type: str = ""

    @property
    def resolved(self) -> bool:
        return self.resolution is None or self.resolution.resolved


def flatten_tag_requests(tags: Iterable[Mapping[str, Any]]) -> tuple[TagRequest, ...]:
    """Return OPC/expression work items from an Ignition tag export.

    UDT instances are flattened by applying instance parameters to the matching
    UDT type definition. Expression payloads are only collected for later eval.
    """

    roots = tuple(tags)
    udt_types = build_udt_type_index(roots)
    requests: list[TagRequest] = []

    for tag in roots:
        if tag.get("tagType") != "UdtType":
            _collect_requests(tag, "", {}, udt_types, requests)

    return tuple(requests)


def build_udt_type_index(tags: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    index: dict[str, Mapping[str, Any]] = {}

    def walk(tag: Mapping[str, Any], parent_path: str) -> None:
        name = str(tag.get("name") or "")
        path = _join_tag_path(parent_path, name)
        if tag.get("tagType") == "UdtType":
            index[_normalize_type_id(path)] = tag
        for child in _children(tag):
            walk(child, path)

    for tag in tags:
        walk(tag, "")
    return index


def extract_expression_references(expression: str) -> tuple[str, ...]:
    resolution = resolve_parameter_binding(expression, {})
    return resolution.unresolved_tokens


def _collect_requests(
    tag: Mapping[str, Any],
    parent_path: str,
    parameters: Mapping[str, Any],
    udt_types: Mapping[str, Mapping[str, Any]],
    requests: list[TagRequest],
) -> None:
    name = str(tag.get("name") or "")
    path = _join_tag_path(parent_path, name)
    context = {**parameters, **_tag_parameters(tag)}

    if tag.get("tagType") == "UdtType":
        return

    if tag.get("tagType") == "UdtInstance":
        type_id = _normalize_type_id(str(tag.get("typeId") or ""))
        udt_type = udt_types.get(type_id)
        if udt_type is not None:
            type_context = {**_tag_parameters(udt_type), **context}
            for child in _children(udt_type):
                _collect_requests(child, path, type_context, udt_types, requests)
        for child in _children(tag):
            _collect_requests(child, path, context, udt_types, requests)
        return

    value_source = tag.get("valueSource")
    if value_source == "opc":
        request = _opc_request(path, tag, context)
        if request is not None:
            requests.append(request)
    elif value_source == "expr" and tag.get("expression") is not None:
        expression = str(tag.get("expression") or "")
        requests.append(TagRequest(tag_path=path, value_source="expr", payload=expression))

    for child in _children(tag):
        _collect_requests(child, path, context, udt_types, requests)


def _opc_request(path: str, tag: Mapping[str, Any], context: Mapping[str, Any]) -> TagRequest | None:
    opc_item_path = tag.get("opcItemPath")
    opc_server = _resolve_optional_binding(tag.get("opcServer"), context)
    data_type = str(tag.get("dataType") or "")
    if isinstance(opc_item_path, Mapping) and opc_item_path.get("bindType") == "parameter":
        template = str(opc_item_path.get("binding") or "")
        resolution = resolve_parameter_binding(template, context)
        return TagRequest(
            tag_path=path,
            value_source="opc",
            payload=resolution.value,
            resolution=resolution,
            opc_server=opc_server,
            data_type=data_type,
        )
    if opc_item_path is not None:
        return TagRequest(
            tag_path=path,
            value_source="opc",
            payload=str(opc_item_path),
            opc_server=opc_server,
            data_type=data_type,
        )
    return None


def _resolve_optional_binding(value: Any, context: Mapping[str, Any]) -> str:
    if isinstance(value, Mapping) and value.get("bindType") == "parameter":
        return resolve_parameter_binding(str(value.get("binding") or ""), context).value
    return str(value or "")


def _tag_parameters(tag: Mapping[str, Any]) -> dict[str, Any]:
    parameters = tag.get("parameters")
    return dict(parameters) if isinstance(parameters, Mapping) else {}


def _children(tag: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    children = tag.get("tags") or tag.get("children") or ()
    return tuple(child for child in children if isinstance(child, Mapping))


def _join_tag_path(parent_path: str, name: str) -> str:
    if not parent_path:
        return name
    if not name:
        return parent_path
    return f"{parent_path}/{name}"


def _normalize_type_id(type_id: str) -> str:
    if type_id.startswith(IGNITION_PROVIDER_PREFIX) and "]" in type_id:
        type_id = type_id.split("]", 1)[1]
    return type_id.strip("/")
