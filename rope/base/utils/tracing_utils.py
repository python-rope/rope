"""
Tracing and debugging functions from Leo.

Duplicated here so that Rope's commit checks won't fail.
"""

import os
import pprint
import sys
from typing import Any, List


def _caller_name(n: int) -> str:
    """Return the name of the caller n levels back in the call stack."""
    try:
        # Get the function name from the call stack.
        frame = sys._getframe(n)  # The stack frame, n levels up.
        code = frame.f_code  # The code object
        locals_ = frame.f_locals  # The local namespace.
        name = code.co_name
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
    """Return the caller name i levels up the call stack."""
    return callers(i + 1).split(",")[0]


def callers(n: int = 4) -> str:
    """
    Return a string containing a comma-separated list of the calling
    function's callers.
    """
    # Be careful to call _caller_name with smaller values of i first:
    # sys._getframe throws ValueError if there are less than i entries.
    i, result = 3, []
    while 1:
        s = _caller_name(n=i)
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
    # Be careful to call _caller_name with smaller values of i first:
    # sys._getframe throws ValueError if there are less than i entries.
    i, result = 3, []
    while 1:
        s = _caller_name(n=i)
        if s:
            result.append(s)
        if not s or len(result) >= n:
            break
        i += 1
    return list(reversed(result))


def format(caller_name: str, module: str, function: str = "") -> str:
    """Format caller_name, module and optional function, aligned for traces."""
    module_s = module.replace("rope.base.", "")
    return f"{caller_name:>10} {module_s:>15}.{function:<15}"


def format_ctor(self: Any) -> str:
    class_s = self.__class__.__name__
    module_s = self.__module__.replace("rope.base.", "")
    return f"{'__init__':>10} {module_s:>15}.{class_s:<15}"


def plural(obj: Any) -> str:
    """Return "s" or "" depending on n."""
    if isinstance(obj, (list, tuple, str)):
        n = len(obj)
    else:
        n = obj
    return "" if n == 1 else "s"


def print_obj(obj: Any, tag: str = None, indent: int = 0) -> None:
    """Pretty print any Python object."""
    print(to_string(obj, indent=indent, tag=tag))


def short_file_name(file_name: str) -> str:
    """Return the base name of a path."""
    return os.path.basename(file_name) if file_name else ""


def split_lines(s: str) -> List[str]:
    """
    Split s into lines, preserving the number of lines and
    the endings of all lines, including the last line.

    This function is not the same as s.splitlines(True).
    """
    return s.splitlines(True) if s else []


def to_string(obj: Any, indent: int = 0, tag: str = None, width: int = 120) -> str:
    """
    Pretty print any Python object to a string.
    """
    if not isinstance(obj, str):
        result = pprint.pformat(obj, indent=indent, width=width)
    elif "\n" not in obj:
        result = repr(obj)
    else:
        # Return the enumerated lines of the string.
        lines = "".join([f"  {i:4}: {z!r}\n" for i, z in enumerate(split_lines(obj))])
        result = f"[\n{lines}]\n"
    return f"{tag.strip()}: {result}" if tag and tag.strip() else result


def trace(*args: Any) -> None:
    """Print the name of the calling function followed by all the args."""
    name = _caller_name(2)
    if name.endswith(".pyc"):
        name = name[:-1]
    args_s = " ".join(str(z) for z in args)
    print(f"{name} {args_s}")
