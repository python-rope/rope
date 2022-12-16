import json

import pytest

from rope.base.serializer import python_to_json, json_to_python


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize(
    "original_data",
    [
        None,
        4,
        "3",
        (),
        [],
        ("hello",),
        (1, [2], "hello"),
        [1, [2], "hello"],
        {"hello": "world"},
        {"hello": ("hello", 1)},
        {("hello", 1): "world"},
        {"4": "hello"},
        {4: "hello"},
    ],
)
def test_roundtrip(original_data, version):
    encoded = python_to_json(original_data, version)
    serialized = json.dumps(encoded)
    decoded = json.loads(serialized)
    rehydrated_data = json_to_python(decoded)

    assert encoded == decoded
    assert rehydrated_data == original_data


@pytest.mark.parametrize(
    "original_data,expected_encoded",
    [
        (None, None),
        (4, 4),
        ("3", "3"),
        ((), {"$": "t", "items": []}),
        ([], []),
        (("hello",), {"$": "t", "items": ["hello",]}),
        ((1, [2], "hello"), {"$": "t", "items": [1, [2], "hello"]}),
        ([1, [2], "hello"], [1, [2], "hello"]),
        ({"hello": "world"}, {"hello": "world"}),
        ({"hello": ("hello", 1)}, {"hello": {"$": "t", "items": ["hello", 1]}}),
    ],
)
def test_expected_encoded_simple(original_data, expected_encoded):
    encoded = python_to_json(original_data)
    serialized = json.dumps(encoded)
    decoded = json.loads(serialized)
    rehydrated_data = json_to_python(decoded)

    assert encoded == decoded
    assert encoded["v"] == 1
    assert encoded["data"] == expected_encoded
    assert encoded["references"] == []
    assert rehydrated_data == original_data



@pytest.mark.parametrize(
    "original_data,expected_encoded,expected_references",
    [
        (
            {("hello", 1): "world"},
            {"0": "world"},
            [{"$": "t", "items": ["hello", 1]}],
        ),
        (
            {"4": "hello"},
            {"0": "hello"},
            ["4"],
        ),
        (
            {4: "hello"},
            {"0": "hello"},
            [4],
        ),
        (
            {None: "hello"},
            {"0": "hello"},
            [None],
        ),
    ],
)
def test_expected_encoded_with_references(original_data, expected_encoded, expected_references):
    encoded = python_to_json(original_data)
    serialized = json.dumps(encoded)
    decoded = json.loads(serialized)
    rehydrated_data = json_to_python(decoded)

    assert encoded == decoded
    assert encoded["v"] == 1
    assert encoded["data"] == expected_encoded
    assert encoded["references"] == expected_references
    assert rehydrated_data == original_data



@pytest.mark.parametrize(
    "original_data,exctype",
    [
        (object(), TypeError),
        (4.8, TypeError),
        ({"$": "hello"}, ValueError),
    ],
)
def test_rejects_unrecognized_object(original_data, exctype):
    with pytest.raises(exctype):
        python_to_json(original_data)
