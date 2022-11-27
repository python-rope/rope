"""AutoImport module for rope."""
from .pickle import AutoImport as _PickleAutoImport
from .sqlite import AutoImport as _SqliteAutoImport
assert _SqliteAutoImport  # Workaround for an apparent pyflakes bug.

AutoImport = _PickleAutoImport

__all__ = ["AutoImport"]
