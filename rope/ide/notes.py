import re

from rope.base import ast


class Codetags(object):

    def __init__(self):
        self.pattern = re.compile('# ([A-Z!?]{2,10}):')

    def tags(self, source):
        result = []
        for lineno, line in enumerate(source.splitlines(False)):
            match = self.pattern.search(line)
            if match:
                result.append((lineno + 1, line[match.start() + 2:]))
        return result


class Errors(object):

    def errors(self, source):
        try:
            ast.parse(source)
        except SyntaxError, e:
            return [(e.lineno, e.msg)]
        except SyntaxWarning:
            pass
        return []


class Warnings(object):

    def warnings(self, source):
        result = []
        try:
            node = ast.parse(source)
        except SyntaxError:
            return []
        except SyntaxWarning, e:
            result.append((e.lineno, e.msg))
        visitor = _WarningsVisitor()
        ast.walk(node, visitor)
        result.extend(visitor.warnings)
        return result


class _WarningsVisitor(object):

    def __init__(self):
        self.definitions = set()
        self.warnings = []

    def _FunctionDef(self, node):
        self._new_definition(node.name, node.lineno)
        self._new_scope(node)

    def _ClassDef(self, node):
        self._new_definition(node.name, node.lineno)
        self._new_scope(node)

    def _Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self._new_name(node.id, node.lineno)

    def _new_name(self, name, lineno):
        if name in self.definitions:
            self.warnings.append(
                (lineno, 'Rebinding defined name <%s>' % name))

    def _new_definition(self, name, lineno):
        self._new_name(name, lineno)
        self.definitions.add(name)

    def _new_scope(self, node):
        visitor = _WarningsVisitor()
        for child in ast.get_child_nodes(node):
            ast.walk(child, visitor)
        self.warnings.extend(visitor.warnings)
