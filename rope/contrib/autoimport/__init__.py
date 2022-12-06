"""AutoImport module for rope."""
from .pickle import AutoImport as _PickleAutoImport


AutoImport = _PickleAutoImport

__all__ = ["AutoImport"]
