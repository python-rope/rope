"""Maintained runtime examples for comparison with native source inference."""

import json


class First:
    pass


class Sibling:
    pass


def identity(value):
    return value


selected = First
if False:
    selected = Sibling
else:
    selected = identity(selected)


class Derived(selected):
    pass


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "selected": selected.__qualname__,
                "ancestry": [base.__qualname__ for base in Derived.__mro__],
            },
            indent=2,
        )
    )
