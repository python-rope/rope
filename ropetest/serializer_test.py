import json

import pytest

from rope.base.serializer import python_to_json, json_to_python


@pytest.mark.parametrize(
    "original_data",
    [
        None,
        4,
        "3",
    ],
)
def test_roundtrip(original_data):
    encoded = python_to_json(original_data)
    serialized = json.dumps(encoded)
    decoded = json.loads(serialized)
    rehydrated_data = json_to_python(decoded)

    assert encoded == decoded
    assert rehydrated_data == original_data
