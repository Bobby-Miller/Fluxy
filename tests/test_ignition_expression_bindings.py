from fluxy.ignition_expression.bindings import extract_binding_tokens, resolve_parameter_binding


def test_resolve_parameter_binding_replaces_context_values():
    result = resolve_parameter_binding(
        "{OPC_Prefix}{OPC_Device}.{IO_Address}F{Interval_Trend}",
        {
            "OPC_Prefix": "",
            "OPC_Device": "DEMO_RTU_01",
            "IO_Address": "40000",
            "Interval_Trend": "<I3>",
        },
    )

    assert result.resolved
    assert result.value == "DEMO_RTU_01.40000F<I3>"
    assert result.unresolved_tokens == ()


def test_resolve_parameter_binding_preserves_unresolved_tokens():
    result = resolve_parameter_binding("{OPC_Device}.{Missing}", {"OPC_Device": "RTU_01"})

    assert not result.resolved
    assert result.value == "RTU_01.{Missing}"
    assert result.unresolved_tokens == ("Missing",)


def test_resolve_nested_parameter_binding_value():
    result = resolve_parameter_binding(
        "{Description}",
        {
            "Description": {
                "value": {"bindType": "parameter", "binding": "{Pad} Well {Ordinal}"},
                "dataType": "String",
            },
            "Pad": "DemoPad",
            "Ordinal": 1,
        },
    )

    assert result.resolved
    assert result.value == "DemoPad Well 1"


def test_extract_binding_tokens():
    assert extract_binding_tokens("{OPC_Device}.{IO_Address}F") == ("OPC_Device", "IO_Address")


def test_resolve_parameter_binding_supports_numeric_offsets():
    result = resolve_parameter_binding(
        "{OPC_Device}.{IO_Address+14}F",
        {"OPC_Device": "RTU_01", "IO_Address": {"dataType": "String", "value": "41600"}},
    )

    assert result.resolved
    assert result.value == "RTU_01.41614F"
    assert result.resolved_tokens["IO_Address+14"] == "41614"
