"""
This module serves to convert a data structure composed of Python primitives
(dict, list, tuple, int, str, None) to JSON-serializable primitives (object,
array, number, str, null).

A core feature of this serializer is that the produced will round-trip to
identical objects when deserialized by the standard library json module.
In other words, this property always holds:

    >>> original_data = ... any JSON ...
    >>> encoded = python_to_json(original_data)
    >>> serialized = json.dumps(encoded)
    >>> decoded = json.loads(serialized)
    >>> rehydrated_data = json_to_python(decoded)

    >>> assert rehydrated_data == original_data
    >>> assert encoded == decoded

Couple challenges in straight serialization that this module helps resolve:

- json.dumps() maps both Python list and tuple to JSON array. This module
  converts Python list `[1, 2, 3]` to `["list", [1, 2, 3]]` and Python tuple
  `(1, 2, 3)` to `["tuple", [1, 2, 3]]`

- Python Dictionary keys can be a tuple, but JSON Object keys must be strings
  This module replaces all `dict` keys with refid which can be resolved using
  the `encoded["references"][refid]` lookup table.

- There is currently no support for floating point numbers.

Note that `json_to_python` only accepts Python objects that can be the output
of `python_to_json`, there is NO guarantee for going the other way around. This
may or may not work:

    >>> python_to_json(json_to_python(original_data)) == original_data

"""


def python_to_json(o):
    references = []
    return {
        "v": 1,
        "data": _py2js(o, references),
        "references": references,
    }


def json_to_python(o):
    assert o["v"] == 1
    references = o["references"]
    data = _js2py(o["data"], references)
    return data


def _py2js(o, references):
    assert not isinstance(o, list)
    if isinstance(o, (str, int)) or o is None:
        return o
    raise TypeError(f"Object of type {type(o)} is not allowed {o}")


def _js2py(o, references):
    assert not isinstance(o, tuple)
    if isinstance(o, (str, int)) or o is None:
        return o
    raise TypeError(f"Object of type {type(o)} is not allowed {o}")
