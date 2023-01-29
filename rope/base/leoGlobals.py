"""
Tracing and debugging functions from Leo.

Duplicated here so that Rope's commit checks won't fail.
"""

# from __future__ import annotations
import os
import sys
from typing import Any, Dict, List


def _callerName(n: int) -> str:
    try:
        # get the function name from the call stack.
        f1 = sys._getframe(n)  # The stack frame, n levels up.
        code1 = f1.f_code  # The code object
        locals_ = f1.f_locals  # The local namespace.
        name = code1.co_name
        # sfn = shortFilename(code1.co_filename)  # The file name.
        # line = code1.co_firstlineno
        obj = locals_.get("self")
        if obj and name == "__init__":
            return f"{obj.__class__.__name__}.{name}"
        return name
    except ValueError:
        # The stack is not deep enough OR
        # sys._getframe does not exist on this platform.
        return ""
    except Exception:
        return ""  # "<no caller name>"


def caller(i: int = 1) -> str:
    """Return the caller name i levels up the stack."""
    return callers(i + 1).split(",")[0]


def callers(n: int = 4) -> str:
    """
    Return a string containing a comma-separated list of the calling
    function's callers.
    """
    # Be careful to call _callerName with smaller values of i first:
    # sys._getframe throws ValueError if there are less than i entries.
    i, result = 3, []
    while 1:
        s = _callerName(n=i)
        if s:
            result.append(s)
        if not s or len(result) >= n:
            break
        i += 1
    return ",".join(reversed(result))


def callers_list(n: int = 4) -> List[str]:
    """
    Return a string containing a comma-separated list of the calling
    function's callers.
    """
    # Be careful to call _callerName with smaller values of i first:
    # sys._getframe throws ValueError if there are less than i entries.
    i, result = 3, []
    while 1:
        s = _callerName(n=i)
        if s:
            result.append(s)
        if not s or len(result) >= n:
            break
        i += 1
    return list(reversed(result))


def get_ctor_name(self, file_name, width=25):
    """Return <module-name>.<class-name>:>20"""
    class_name = self.__class__.__name__
    module_name = shortFileName(file_name).replace(".py", "")
    combined_name = f"{module_name}.{class_name}"
    padding = " " * max(0, 25 - len(combined_name))
    return f"{padding}{combined_name}"


def plural(obj: Any) -> str:
    """Return "s" or "" depending on n."""
    if isinstance(obj, (list, tuple, str)):
        n = len(obj)
    else:
        n = obj
    return "" if n == 1 else "s"


def printObj(obj: Any, indent: str = "", tag: str = None) -> None:
    """Pretty print any Python object"""
    print(objToString(obj, indent=indent, tag=tag))


def objToString(
    obj: Any, indent: str = "", tag: str = "", concise: bool = False
) -> str:
    """
    Pretty print any Python object to a string.

    concise=False: (Legacy) return a detailed string.
    concise=True: Return a summary string.
    """
    if tag:
        print(tag.strip())
    if concise:
        r = repr(obj)
        if obj is None:
            return f"{indent}None"
        if isinstance(obj, dict):
            return f"{indent}dict: {len(obj.keys())} keys"
        if isinstance(obj, list):
            return f"{indent}list: {len(obj)} items plural(len(obj))"
        if isinstance(obj, tuple):
            return f"{indent}tuple: {len(obj)} item{plural(len(obj))}"
        if "method" in r:
            return f"{indent}method: {obj.__name__}"
        if "class" in r:
            return f"{indent}class"
        if "module" in r:
            return f"{indent}module"
        return f"{indent}object: {obj!r}"

    # concise = False
    if isinstance(obj, dict):
        return dictToString(obj, indent=indent)
    if isinstance(obj, list):
        return listToString(obj, indent=indent)
    if isinstance(obj, tuple):
        return tupleToString(obj, indent=indent)
    if isinstance(obj, str):
        # Print multi-line strings as lists.
        lines = splitLines(obj)
        if len(lines) > 1:
            return listToString(lines, indent=indent)
    return f"{indent} {obj!r}"


def dictToString(d: Dict[str, str], indent: str = "", tag: str = None) -> str:
    """Pretty print a Python dict to a string."""
    # pylint: disable=unnecessary-lambda
    if not d:
        return "{}"
    result = ["{\n"]
    indent2 = indent + " " * 4
    n = 2 + len(indent) + max([len(repr(z)) for z in d.keys()])
    for i, key in enumerate(sorted(d, key=lambda z: repr(z))):
        pad = " " * max(0, (n - len(repr(key))))
        result.append(f"{pad}{key}:")
        result.append(objToString(d.get(key), indent=indent2))
        if i + 1 < len(d.keys()):
            result.append(",")
        result.append("\n")
    result.append(indent + "}")
    s = "".join(result)
    return f"{tag}...\n{s}\n" if tag else s


def listToString(obj: Any, indent: str = "", tag: str = None) -> str:
    """Pretty print a Python list to a string."""
    if not obj:
        return indent + "[]"
    result = [indent, "["]
    indent2 = indent + " " * 4
    # I prefer not to compress lists.
    for i, obj2 in enumerate(obj):
        result.append("\n" + indent2)
        result.append(objToString(obj2, indent=indent2))
        if i + 1 < len(obj) > 1:
            result.append(",")
        else:
            result.append("\n" + indent)
    result.append("]")
    s = "".join(result)
    return f"{tag}...\n{s}\n" if tag else s


def tupleToString(obj: Any, indent: str = "", tag: str = None) -> str:
    """Pretty print a Python tuple to a string."""
    if not obj:
        return "(),"
    result = ["("]
    indent2 = indent + " " * 4
    for i, obj2 in enumerate(obj):
        if len(obj) > 1:
            result.append("\n" + indent2)
        result.append(objToString(obj2, indent=indent2))
        if len(obj) == 1 or i + 1 < len(obj):
            result.append(",")
        elif len(obj) > 1:
            result.append("\n" + indent)
    result.append(")")
    s = "".join(result)
    return f"{tag}...\n{s}\n" if tag else s


def shortFileName(fileName: str, n: int = None) -> str:
    """Return the base name of a path."""
    if n is not None:
        trace('"n" keyword argument is no longer used')
    return os.path.basename(fileName) if fileName else ""


shortFilename = shortFileName


def splitLines(s: str) -> List[str]:
    """
    Split s into lines, preserving the number of lines and
    the endings of all lines, including the last line.
    """
    return s.splitlines(True) if s else []  # This is a Python string function!


splitlines = splitLines


def trace(*args: Any) -> None:
    """Print the name of the calling function followed by all the args."""
    name = _callerName(2)
    if name.endswith(".pyc"):
        name = name[:-1]
    args = "".join(str(z) for z in args)
    print(f"{name} {args}")
