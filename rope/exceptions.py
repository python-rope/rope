class RopeException(Exception):
    """Base exception for rope"""


class ModuleNotFoundException(RopeException):
    """Module not found exception"""


class AttributeNotFoundException(RopeException):
    """Attribute not found exception"""


class NameNotFoundException(RopeException):
    """Attribute not found exception"""


class RopeUIException(RopeException):
    """Base exception for user interface parts of rope"""

