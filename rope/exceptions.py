class RopeException(Exception):
    """Base exception for rope"""


class ModuleNotFoundException(RopeException):
    """Module not found exception"""


class AttributeNotFoundException(RopeException):
    """Attribute not found exception"""


class NameNotFoundException(RopeException):
    """Attribute not found exception"""


class RefactoringException(RopeException):
    """Errors for performing a refactoring"""


class RopeUIException(RopeException):
    """Base exception for user interface parts of rope"""

