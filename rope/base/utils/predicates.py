"""An experimental module containing predicates to replace `Abstract` classes.

"""

import rope.base.builtins as builtins
import rope.base.pyobjects as pyobjects


def is_abstract_class(obj):
    return isinstance(
        obj,
        (
            builtins.BuiltinClass,
            pyobjects.PyClass,
            builtins.Generator,
            builtins.Iterator,
        ),
    )


def is_abstract_function(obj):
    return isinstance(
        obj, (builtins.BuiltinFunction, builtins.Lambda, pyobjects.PyFunction)
    )


def is_abstract_module(obj):
    return isinstance(obj, (builtins.BuiltinModule, pyobjects._PyModule))
