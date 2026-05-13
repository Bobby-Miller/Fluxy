from fluxy.ignition_expression import extract_expression_references, flatten_tag_requests


def test_flatten_tag_requests_resolves_udt_instance_opc_paths():
    requests = flatten_tag_requests(
        [
            {
                "name": "_types_",
                "tagType": "Folder",
                "tags": [
                    {
                        "name": "Well",
                        "tagType": "UdtType",
                        "parameters": {
                            "OPC_Prefix": {"dataType": "String", "value": "ns=2;s="},
                            "Interval_Trend": {"dataType": "String", "value": "<I3>"},
                        },
                        "tags": [
                            {
                                "name": "CASING_PRESSURE",
                                "tagType": "AtomicTag",
                                "valueSource": "opc",
                                "dataType": "Float4",
                                "opcServer": {"bindType": "parameter", "binding": "{OPC_Server}"},
                                "opcItemPath": {
                                    "bindType": "parameter",
                                    "binding": "{OPC_Prefix}{OPC_Device}.{IO_Address}{Interval_Trend}",
                                },
                            }
                        ],
                    }
                ],
            },
            {
                "name": "Pad_A",
                "tagType": "Folder",
                "tags": [
                    {
                        "name": "Well_01",
                        "tagType": "UdtInstance",
                        "typeId": "[Tag_02]_types_/Well",
                        "parameters": {
                            "OPC_Server": {"dataType": "String", "value": "ACM_02"},
                            "OPC_Device": {"dataType": "String", "value": "RTU_01"},
                            "IO_Address": {"dataType": "String", "value": "41600F"},
                        },
                    }
                ],
            },
        ]
    )

    assert len(requests) == 1
    assert requests[0].tag_path == "Pad_A/Well_01/CASING_PRESSURE"
    assert requests[0].value_source == "opc"
    assert requests[0].payload == "ns=2;s=RTU_01.41600F<I3>"
    assert requests[0].opc_server == "ACM_02"
    assert requests[0].data_type == "Float4"
    assert requests[0].resolved


def test_flatten_tag_requests_collects_expression_payloads():
    requests = flatten_tag_requests(
        [
            {
                "name": "Total",
                "tagType": "AtomicTag",
                "valueSource": "expr",
                "expression": "{[.]A} + {[.]../B}",
            }
        ]
    )

    assert requests[0].tag_path == "Total"
    assert requests[0].value_source == "expr"
    assert requests[0].payload == "{[.]A} + {[.]../B}"


def test_extract_expression_references_returns_tag_reference_tokens():
    assert extract_expression_references("if({[.]Running}, {[.]Rate}, 0)") == ("[.]Running", "[.]Rate")
