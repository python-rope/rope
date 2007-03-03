import re
import compiler


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
            compiler.parse(source)
        except SyntaxError, e:
            return [(e.lineno, e.msg)]
        except SyntaxWarning:
            pass
        return []


class Warnings(object):

    def warnings(self, source):
        result = []
        try:
            ast = compiler.parse(source)
        except SyntaxError:
            return []
        except SyntaxWarning, e:
            result.append((e.lineno, e.msg))
        visitor = _WarningsVisitor()
        compiler.walk(ast, visitor)
        result.extend(visitor.warnings)
        return result


class _WarningsVisitor(object):

    def __init__(self):
        self.definitions = set()
        self.warnings = []

    def visitFunction(self, node):
        self._new_definition(node.name, node.lineno)
        self._new_scope(node)

    def visitClass(self, node):
        self._new_definition(node.name, node.lineno)
        self._new_scope(node)

    def visitAssName(self, node):
        self._new_name(node.name, node.lineno)

    def _new_name(self, name, lineno):
        if name in self.definitions:
            self.warnings.append(
                (lineno, 'Rebinding defined name <%s>' % name))

    def _new_definition(self, name, lineno):
        self._new_name(name, lineno)
        self.definitions.add(name)

    def _new_scope(self, node):
        visitor = _WarningsVisitor()
        for child in node.getChildNodes():
            compiler.walk(child, visitor)
        self.warnings.extend(visitor.warnings)
