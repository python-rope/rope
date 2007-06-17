import re

from rope.base import ast, codeanalyze
from rope.refactor import patchedast, similarfinder


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
        result.extend(self._find_self_assignments(node, source))
        result.sort(cmp=lambda o1, o2: cmp(o1[0], o2[0]))
        return result

    def _find_self_assignments(self, node, source):
        result = []
        finder = similarfinder.SimilarFinder(source, node)
        lines = codeanalyze.SourceLinesAdapter(source)
        for self_assignment in finder.get_matches('${?a} = ${?a}'):
            region = patchedast.node_region(self_assignment.get_ast('?a'))
            message = 'Assigning <%s> to itself' % source[region[0]:region[1]]
            lineno = lines.get_line_number(self_assignment.get_region()[0])
            result.append((lineno, message))
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
