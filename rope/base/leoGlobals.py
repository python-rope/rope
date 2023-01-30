"""
Tracing and debugging functions from Leo.

Duplicated here so that Rope's commit checks won't fail.
"""

# from __future__ import annotations
import os
import pprint
import sys
from typing import Any, List


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


def get_ctor_name(self: Any, file_name: str, width: int = 25):
    """Return <module-name>.<class-name>:>width"""
    class_name = self.__class__.__name__
    module_name = shortFileName(file_name).replace(".py", "")
    combined_name = f"{module_name}.{class_name}"
    padding = " " * max(0, 25 - len(combined_name))
    return f"{padding}{combined_name}"


def objToString(obj: Any, indent: int = 0, width: int = 120) -> str:
    """
    Pretty print any Python object to a string.
    """

    s = pprint.pformat(
        obj,
        compact=False,
        depth=None,
        # indent=len(indent) if isinstance(indent, str) else indent,
        indent=indent,
        sort_dicts=True,
        # underscore_numbers=False,
        width=width,
    )
    if s and isinstance(obj, str) and "\n" in s:
        # Weird: strip ()
        if s[0] == "(":
            s = s[1:]
        if s and s[-1] == ")":
            s = s[:-1]
        results = ["[\n"]
        for i, z in enumerate(splitLines(s)):
            results.append(f"  {i:4}: {z!s}")
        results.append("\n]\n")
        return "".join(results)
    return s


def plural(obj: Any) -> str:
    """Return "s" or "" depending on n."""
    if isinstance(obj, (list, tuple, str)):
        n = len(obj)
    else:
        n = obj
    return "" if n == 1 else "s"


def printObj(obj: Any, tag: str = None, indent: int = 0) -> None:
    """Pretty print any Python object using g.pr."""
    if tag:
        print(tag.strip())
    print(objToString(obj, indent=indent))


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
