import compiler.ast
import compiler.consts
import re

from rope.base import codeanalyze, exceptions


def get_patched_ast(source):
    """Adds `region` and `sorted_children` fields to nodes"""
    ast = compiler.parse(source)
    call_for_nodes(ast, _PatchingASTWalker(source))
    return ast


def call_for_nodes(ast, callback, recursive=False):
    """If callback returns `True` the child nodes are skipped"""
    result = callback(ast)
    if recursive and not result:
        for child in ast.getChildNodes():
            call_for_nodes(child, callback, recursive)

def write_ast(ast):
    """Extract source form a patched AST"""
    result = []
    for child in ast.sorted_children:
        if isinstance(child, compiler.ast.Node):
            result.append(write_ast(child))
        else:
            result.append(child)
    return ''.join(result)


class MismatchedTokenError(exceptions.RopeError):
    pass

class _PatchingASTWalker(object):

    def __init__(self, source):
        self.source = _Source(source)

    Number = object()
    String = object()

    def __call__(self, node):
        method = getattr(self, 'visit' + node.__class__.__name__, None)
        if method is not None:
            return method(node)
        # ???: Unknown node; What should we do here?
        raise RuntimeError('Unknown node type <%s>' %
                           node.__class__.__name__)

    def _handle(self, node, base_children, eat_parens=False, eat_spaces=False):
        children = []
        suspected_start = self.source.offset
        start = suspected_start
        first_token = True
        for child in base_children:
            if child is None:
                continue
            offset = self.source.offset
            if isinstance(child, compiler.ast.Node):
                call_for_nodes(child, self)
                token_start = child.region[0]
            else:
                if child is self.String:
                    region = self.source.consume_string()
                elif child is self.Number:
                    region = self.source.consume_number()
                else:
                    region = self.source.consume(child)
                child = self.source.get(region[0], region[1])
                token_start = region[0]
            if not first_token:
                children.append(self.source.get(offset, token_start))
            else:
                first_token = False
                start = token_start
            children.append(child)
        start = self._handle_parens(children, start)
        if eat_parens:
            start = self._eat_surrounding_parens(
                children, suspected_start, start)
        if eat_spaces:
            children.insert(0, self.source[0:start])
            end_spaces = self.source[self.source.offset:]
            self.source.consume(end_spaces)
            children.append(end_spaces)
            start = 0
        node.sorted_children = children
        node.region = (start, self.source.offset)

    def _handle_parens(self, children, start):
        """Changes `children` and returns new start"""
        opens, closes = self._count_needed_parens(children)
        old_end = self.source.offset
        new_end = None
        for i in range(closes):
            new_end = self.source.consume(')')[1]
        if new_end is not None:
            children.append(self.source.get(old_end, new_end))
        new_start = None
        for i in range(opens):
            new_start = self.source.find_backwards('(', start)
        if new_start is not None:
            children.insert(0, self.source.get(new_start, start))
            start = new_start
        return start

    def _eat_surrounding_parens(self, children, suspected_start, start):
        if '(' in self.source[suspected_start:start]:
            old_start = start
            old_offset = self.source.offset
            start = self.source.find_backwards('(', start)
            children.insert(0, '(')
            children.insert(1, self.source[start + 1:old_start])
            token_start, token_end = self.source.consume(')')
            children.append(self.source[old_offset:token_start])
            children.append(')')
        return start

    def _count_needed_parens(self, children):
        start = 0
        opens = 0
        for child in children:
            if not isinstance(child, basestring):
                continue
            if child == '' or child[0] in '\'"':
                continue
            index = 0
            while index < len(child):
                if child[index] == ')':
                    if opens > 0:
                        opens -= 1
                    else:
                        start += 1
                if child[index] == '(':
                    opens += 1
                if child[index] == '#':
                    try:
                        index = child.index('\n', index)
                    except ValueError:
                        break
                index += 1
        return start, opens

    def visitAdd(self, node):
        self._handle(node, [node.left, '+', node.right])

    def visitAnd(self, node):
        self._handle(node, self._child_nodes(node.nodes, 'and'))

    def visitAssAttr(self, node):
        self._handle(node, [node.expr, '.', node.attrname])

    def visitAssList(self, node):
        children = self._child_nodes(node.nodes, ',')
        children.insert(0, '[')
        children.append(']')
        self._handle(node, children)

    def visitAssName(self, node):
        self._handle(node, [node.name])

    def visitAssTuple(self, node):
        self._handle_tuple(node)

    def visitAssert(self, node):
        children = ['assert', node.test]
        if node.fail:
            children.append(',')
            children.append(node.fail)
        self._handle(node, children)

    def visitAssign(self, node):
        children = self._child_nodes(node.nodes, '=')
        children.append('=')
        children.append(node.expr)
        self._handle(node, children)

    def visitAugAssign(self, node):
        self._handle(node, [node.node, node.op, node.expr])

    def visitBackquote(self, node):
        self._handle(node, ['`', node.expr, '`'])

    def visitBitand(self, node):
        self._handle(node, self._child_nodes(node.nodes, '&'))

    def visitBitor(self, node):
        self._handle(node, self._child_nodes(node.nodes, '|'))

    def visitBitxor(self, node):
        self._handle(node, self._child_nodes(node.nodes, '^'))

    def visitBreak(self, node):
        self._handle(node, ['break'])

    def visitCallFunc(self, node):
        children = []
        children.append(node.node)
        children.append('(')
        children.extend(self._child_nodes(node.args, ','))
        if node.star_args is not None:
            if node.args:
                children.append(',')
            children.extend(['*', node.star_args])
        if node.dstar_args is not None:
            if node.args:
                children.append(',')
            children.extend(['**', node.dstar_args])
        children.append(')')
        self._handle(node, children)

    def visitClass(self, node):
        children = []
        children.extend(['class', node.name])
        if node.bases:
            children.append('(')
            children.extend(self._child_nodes(node.bases, ','))
            children.append(')')
        children.append(':')
        if node.doc is not None:
            children.append(self.String)
        children.append(node.code)
        self._handle(node, children)

    def visitCompare(self, node):
        children = []
        children.append(node.expr)
        for op, child in node.ops:
            children.append(op)
            children.append(child)
        self._handle(node, children)

    def visitConst(self, node):
        value = repr(node.value)
        if isinstance(node.value, (int, long, float, complex)):
            value = self.Number
        if isinstance(node.value, basestring):
            value = self.String
        self._handle(node, [value])

    def visitContinue(self, node):
        self._handle(node, ['continue'])

    def visitDecorators(self, node):
        self._handle(node, ['@'] + self._child_nodes(node.nodes, '@'))

    def visitDict(self, node):
        children = []
        children.append('{')
        for index, (key, value) in enumerate(node.items):
            children.extend([key, ':', value])
            if index < len(node.items) - 1:
                children.append(',')
        children.append('}')
        self._handle(node, children)

    def visitDiscard(self, node):
        self._handle(node, [node.expr])

    def visitDiv(self, node):
        self._handle(node, [node.left, '/', node.right])

    def visitEllipsis(self, node):
        self._handle(node, ['...'])

    def visitExpression(self, node):
        self._handle(node, [node.node])

    def visitExec(self, node):
        children = []
        children.extend(['exec', node.expr])
        if node.locals:
            children.extend(['in', node.locals])
        if node.globals:
            children.extend([',', node.globals])
        self._handle(node, children)

    def visitFloorDiv(self, node):
        self._handle(node, [node.left, '//', node.right])

    def visitFor(self, node):
        children = ['for', node.assign, 'in', node.list, ':', node.body]
        if node.else_:
            children.extend(['else', ':', node.else_])
        self._handle(node, children)

    def visitFrom(self, node):
        children = ['from']
        if hasattr(node, 'level') and node.level > 0:
            children.append('.' * node.level)
        children.extend([node.modname, 'import'])
        for index, (name, alias) in enumerate(node.names):
            children.append(name)
            if alias is not None:
                children.extend(['as', alias])
            if index < len(node.names) - 1:
                children.append(',')
        self._handle(node, children)

    def visitFunction(self, node):
        children = []
        if node.decorators:
            children.append(node.decorators)
        children.extend(['def', node.name, '('])
        children.extend(self._arg_list(node.argnames, node.defaults,
                                       node.flags))
        children.extend([')', ':'])
        if node.doc:
            children.append(self.String)
        children.append(node.code)
        self._handle(node, children)

    def _arg_list(self, argnames, defaults, flags):
        children = []
        args = list(argnames)
        dstar_args = None
        if flags & compiler.consts.CO_VARKEYWORDS:
            dstar_args = args.pop()
        star_args = None
        if flags & compiler.consts.CO_VARARGS:
            star_args = args.pop()
        defaults = [None] * (len(args) - len(defaults)) + list(defaults)
        for arg, default in zip(args[:-1], defaults[:-1]):
            self._add_args_to_children(children, arg, default)
            children.append(',')
        if args:
            self._add_args_to_children(children, args[-1], defaults[-1])
        if star_args is not None:
            if args:
                children.append(',')
            children.extend(['*', star_args])
        if dstar_args is not None:
            if args:
                children.append(',')
            children.extend(['**', dstar_args])
        return children

    def _add_args_to_children(self, children, arg, default):
        children.append(arg)
        if default is not None:
            children.append('=')
            children.append(default)

    def visitGenExpr(self, node):
        self._handle(node, [node.code], eat_parens=True)

    def visitGenExprFor(self, node):
        children = ['for', node.assign, 'in', node.iter]
        if node.ifs:
            children.extend(node.ifs)
        self._handle(node, children)

    def visitGenExprIf(self, node):
        self._handle(node, ['if', node.test])

    def visitGenExprInner(self, node):
        self._handle(node, [node.expr] + node.quals)

    def visitGetattr(self, node):
        self._handle(node, [node.expr, '.', node.attrname])

    def visitGlobal(self, node):
        children = self._child_nodes(node.names, ',')
        children.insert(0, 'global')
        self._handle(node, children)

    def visitIf(self, node):
        children = ['if', node.tests[0][0], ':', node.tests[0][1]]
        for test, body in node.tests[1:]:
            children.extend(['elif', test, ':', body])
        if node.else_:
            children.extend(['else', ':', node.else_])
        self._handle(node, children)

    def visitImport(self, node):
        children = ['import']
        for index, (name, alias) in enumerate(node.names):
            if index != 0:
                children.append(',')
            children.append(name)
            if alias is not None:
                children.extend(['as', alias])
        self._handle(node, children)

    def visitInvert(self, node):
        self._handle(node, ['~', node.expr])

    def visitKeyword(self, node):
        self._handle(node, [node.name, '=', node.expr])

    def visitLambda(self, node):
        children = ['lambda']
        children.extend(self._arg_list(node.argnames, node.defaults,
                                       node.flags))
        children.extend([':', node.code])
        self._handle(node, children)

    def visitLeftShift(self, node):
        self._handle(node, [node.left, '<<', node.right])

    def visitList(self, node):
        self._handle(node, ['['] + self._child_nodes(node.nodes, ',') + [']'])

    def visitListCompFor(self, node):
        children = ['for', node.assign, 'in', node.list]
        if node.ifs:
            children.extend(node.ifs)
        self._handle(node, children)

    def visitListCompIf(self, node):
        self._handle(node, ['if', node.test])

    def visitListComp(self, node):
        self._handle(node, ['[', node.expr] + node.quals + [']'])

    def visitMod(self, node):
        self._handle(node, [node.left, '%', node.right])

    def visitModule(self, node):
        doc = None
        if node.doc is not None:
            doc = self.String
        self._handle(node, [doc, node.node], eat_spaces=True)

    def visitMul(self, node):
        self._handle(node, [node.left, '*', node.right])

    def visitName(self, node):
        self._handle(node, [node.name])

    def visitNot(self, node):
        self._handle(node, ['not', node.expr])

    def visitOr(self, node):
        self._handle(node, self._child_nodes(node.nodes, 'or'))

    def visitPass(self, node):
        self._handle(node, ['pass'])

    def visitPower(self, node):
        self._handle(node, [node.left, '**', node.right])

    def visitPrint(self, node):
        children = self._base_print(node)
        children.append(',')
        self._handle(node, children)

    def visitPrintnl(self, node):
        self._handle(node, self._base_print(node))

    def _base_print(self, node):
        children = ['print']
        if node.dest:
            children.extend(['>>', node.dest, ','])
        children.extend(self._child_nodes(node.nodes, ','))
        return children

    def visitRaise(self, node):
        children = ['raise']
        if node.expr1:
            children.append(node.expr1)
        if node.expr2:
            children.append(',')
            children.append(node.expr2)
        if node.expr3:
            children.append(',')
            children.append(node.expr3)
        self._handle(node, children)

    def visitReturn(self, node):
        children = ['return']
        if node.value and not (isinstance(node.value, compiler.ast.Const) and
                               node.value.value == None):
            children.append(node.value)
        self._handle(node, children)

    def visitRightShift(self, node):
        self._handle(node, [node.left, '>>', node.right])

    def visitSlice(self, node):
        children = [node.expr, '[']
        if node.lower:
            children.append(node.lower)
        children.append(':')
        if node.lower:
            children.append(node.upper)
        children.append(']')
        self._handle(node, children)

    def visitStmt(self, node):
        self._handle(node, node.nodes)

    def visitSub(self, node):
        self._handle(node, [node.left, '-', node.right])

    def visitSubscript(self, node):
        self._handle(node, [node.expr, '['] +
                            self._child_nodes(node.subs, ',') + [']'])

    def visitTuple(self, node):
        self._handle_tuple(node)

    def visitTryFinally(self, node):
        children = []
        if not isinstance(node.body, compiler.ast.TryExcept):
            children.extend(['try', ':'])
        children.extend([node.body, 'finally', ':', node.final])
        self._handle(node, children)

    def visitTryExcept(self, node):
        children = ['try', ':', node.body]
        for exception, name, body in node.handlers:
            children.append('except')
            if exception:
                children.append(exception)
            if name:
                children.extend([',', name])
            children.extend([':', body])
        if node.else_:
            children.extend(['else', ':', node.else_])
        self._handle(node, children    )

    def _handle_tuple(self, node):
        self._handle(node, self._child_nodes(node.nodes, ','), eat_parens=True)

    def visitUnaryAdd(self, node):
        self._handle(node, ['+', node.expr])

    def visitUnarySub(self, node):
        self._handle(node, ['-', node.expr])

    def visitYield(self, node):
        children = ['yield']
        if node.value:
            children.append(node.value)
        self._handle(node, children)

    def visitWhile(self, node):
        children = ['while', node.test, ':', node.body]
        if node.else_:
            children.extend(['else', ':', node.else_])
        self._handle(node, children)

    def visitWith(self, node):
        children = ['with', node.expr]
        if node.vars:
            children.extend(['as', node.vars])
        children.extend([':', node.body])
        self._handle(node, children)

    def _child_nodes(self, nodes, separator):
        children = []
        for index, child in enumerate(nodes):
            children.append(child)
            if index < len(nodes) - 1:
                children.append(separator)
        return children


class _Source(object):

    def __init__(self, source):
        self.source = source
        self.offset = 0

    def consume(self, token):
        try:
            while True:
                new_offset = self.source.index(token, self.offset)
                if self._good_token(token, new_offset):
                    break
                else:
                    self._skip_comment()
        except (ValueError, TypeError):
            raise MismatchedTokenError(
                'Token <%s> at %s cannot be matched' %
                (token, self._get_location()))
        self.offset = new_offset + len(token)
        return (new_offset, self.offset)

    def _good_token(self, token, offset):
        """Checks whether consumed token is in comments"""
        return not '#' in self.source[self.offset:offset]

    def _skip_comment(self):
        self.offset = self.source.index('\n', self.offset + 1)

    def _get_location(self):
        lines = self.source[:self.offset].split('\n')
        return (len(lines), len(lines[-1]))

    def consume_string(self):
        if _Source._string_pattern is None:
            original = codeanalyze.get_string_pattern()
            pattern = r'(%s)((\s|\\\n)*(%s))*' % (original, original)
            _Source._string_pattern = re.compile(pattern)
        repattern = _Source._string_pattern
        return self._consume_pattern(repattern)

    def consume_number(self):
        if _Source._number_pattern is None:
            _Source._number_pattern = re.compile(
                self._get_number_pattern())
        repattern = _Source._number_pattern
        return self._consume_pattern(repattern)

    def _consume_pattern(self, repattern):
        while True:
            match = repattern.search(self.source, self.offset)
            if self._good_token(match.group(), match.start()):
                break
            else:
                self._skip_comment()
        self.offset = match.end()
        return match.start(), match.end()

    def till_token(self, token):
        new_offset = self.source.index(token, self.offset)
        return self.get(self.offset, new_offset)

    def get(self, start, end):
        return self.source[start:end]

    def from_offset(self, offset):
        return self.get(offset, self.offset)

    def find_backwards(self, pattern, offset):
        return self.source.rindex(pattern, 0, offset)

    def __getitem__(self, index):
        return self.source[index]

    def __getslice__(self, i, j):
        return self.source[i:j]

    def _get_number_pattern(self):
        # We should handle integer, long_integer, others, imagnumber
        # HACK: An approaximation does the job
        integer = r'(0|0x)?[\da-fA-F]+[lL]?'
        return r'(%s(\.\d*)?|(\.\d+))([eE][-+]?\d*)?[jJ]?' % integer

    _string_pattern = None
    _number_pattern = None
