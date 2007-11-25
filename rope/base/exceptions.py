class RopeError(Exception):
    """Base exception for rope"""


class ResourceNotFoundError(RopeError):
    """Resource not found exception"""


class RefactoringError(RopeError):
    """Errors for performing a refactoring"""


class InterruptedTaskError(RopeError):
    """Errors for performing a refactoring"""


class HistoryError(RopeError):
    """Errors for history undo/redo operations"""


class ModuleNotFoundError(RopeError):
    """Module not found exception"""


class AttributeNotFoundError(RopeError):
    """Attribute not found exception"""


class NameNotFoundError(RopeError):
    """Attribute not found exception"""


class ModuleSyntaxError(RopeError):
    """Module has syntax errors"""
