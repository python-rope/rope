import json

import pytest

from rope.base.serializer import _js2py, json_to_python, python_to_json


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
        [1, (2,), "hello"],
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


def expected_encoded_simple_data(version):
    data = [
        (None, None),
        (4, 4),
        ("3", "3"),
        ({"hello": "world"}, {"hello": "world"}),
    ]
    return [[*d, version] for d in data]

@pytest.mark.parametrize(
    "original_data,expected_encoded,version",
    [
        *expected_encoded_simple_data(version=1),
        *expected_encoded_simple_data(version=2),

        ((), {"$": "t", "items": []}, 1),
        ([], [], 1),
        (("hello",), {"$": "t", "items": ["hello"]}, 1),
        ((1, [2], "hello"), {"$": "t", "items": [1, [2], "hello"]}, 1),
        ([1, (2,), "hello"], [1, {"$": "t", "items": [2]}, "hello"], 1),
        ({"hello": ("hello", 1)}, {"hello": {"$": "t", "items": ["hello", 1]}}, 1),

        ((), [], 2),
        ([], {"$": "l", "items": []}, 2),
        (("hello",), ["hello"], 2),
        ((1, [2], "hello"), [1, {"$": "l", "items": [2]}, "hello"], 2),
        ([1, (2,), "hello"], {"$": "l", "items": [1, [2], "hello"]}, 2),
        ({"hello": ("hello", 1)}, {"hello": ["hello", 1]}, 2),
    ],
)
def test_expected_encoded_simple(original_data, expected_encoded, version):
    encoded = python_to_json(original_data, version)
    serialized = json.dumps(encoded)
    decoded = json.loads(serialized)
    rehydrated_data = json_to_python(decoded)

    assert encoded == decoded
    assert encoded["v"] == version
    assert encoded["data"] == expected_encoded, (original_data, version)
    assert "references" not in encoded
    assert rehydrated_data == original_data


@pytest.mark.parametrize(
    "original_data,expected_encoded,expected_references,version",
    [
        (
            {("hello", 1): "world"},
            {"0": "world"},
            [{"$": "t", "items": ["hello", 1]}],
            1,
        ),
        (
            {"4": "hello"},
            {"0": "hello"},
            ["4"],
            1,
        ),
        (
            {4: "hello"},
            {"0": "hello"},
            [4],
            1,
        ),
        (
            {None: "hello"},
            {"0": "hello"},
            [None],
            1,
        ),
    ],
)
def test_expected_encoded_with_references(original_data, expected_encoded, expected_references, version):
    encoded = python_to_json(original_data, version)
    serialized = json.dumps(encoded)
    decoded = json.loads(serialized)
    rehydrated_data = json_to_python(decoded)

    assert encoded == decoded
    assert encoded["v"] == 1
    assert encoded["data"] == expected_encoded
    assert encoded["references"] == expected_references
    assert rehydrated_data == original_data



@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize(
    "original_data,exctype",
    [
        (object(), TypeError),
        (4.8, TypeError),
        ({"$": "hello"}, ValueError),
    ],
)
def test_rejects_unrecognized_object(original_data, exctype, version):
    with pytest.raises(exctype):
        python_to_json(original_data, version)


def test_unexpected_version_python_to_json():
    with pytest.raises(ValueError, match="Unexpected version"):
        python_to_json({"hello": ["world"]}, version=-123456)


def test_unexpected_version_json_to_python():
    modified = python_to_json({"hello": ["world"]})
    modified["v"] = -123456
    assert isinstance(modified["data"]["hello"], list)

    with pytest.raises(ValueError, match="Unexpected version"):
        json_to_python(modified)

    with pytest.raises(ValueError, match="Unexpected version"):
        _js2py(modified["data"], {}, modified["v"])


def test_unexpected_dollar_object_type():
    modified = python_to_json({"hello": ["world"]})
    modified["data"]["$"] = "unexpected"

    with pytest.raises(TypeError, match="Unrecognized object of type"):
        json_to_python(modified)


def test_unexpected_object_type():
    modified = python_to_json({"hello": ["world"]})
    modified["data"]["hello"] = ()

    with pytest.raises(TypeError, match='Object of type "tuple" is not allowed'):
        json_to_python(modified)
