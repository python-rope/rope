import unittest

from rope.refactor import patchedast


class PatchedASTTest(unittest.TestCase):

    def setUp(self):
        super(PatchedASTTest, self).setUp()

    def tearDown(self):
        super(PatchedASTTest, self).tearDown()

    def test_integer_literals_and_region(self):
        source = 'a = 10\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        start = source.index('10')
        checker.check_region('Const(10)', start, start + 2)

    def test_integer_literals_and_sorted_children(self):
        source = 'a = 10\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        start = source.index('10')
        checker.check_children('Const(10)', ['10'])

    def test_ass_name_node(self):
        source = 'a = 10\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        start = source.index('a')
        checker.check_region('AssName', start, start + 1)
        checker.check_children('AssName', ['a'])

    def test_assign_node(self):
        source = 'a = 10\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        start = source.index('a')
        checker.check_region('Assign', 0, len(source) - 1)
        checker.check_children(
            'Assign', ['AssName', ' ', '=', ' ', 'Const'])

    def test_add_node(self):
        source = '1 + 2\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Add', 0, len(source) - 1)
        checker.check_children(
            'Add', ['Const(1)', ' ', '+', ' ', 'Const(2)'])

    def test_and_node(self):
        source = 'True and True\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('And', 0, len(source) - 1)
        checker.check_children(
            'And', ['Name', ' ', 'and', ' ', 'Name'])

    def test_basic_closing_parens(self):
        source = '1 + (2)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        two_start = source.index('2')
        checker.check_region('Const(2)', two_start, two_start + 1)
        checker.check_children('Const(2)', ['2'])
        checker.check_region('Add', 0, len(source) - 1)
        checker.check_children(
            'Add', ['Const(1)', ' ', '+', ' (', 'Const(2)', ')'])

    def test_basic_opening_parens(self):
        source = '(1) + 2\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Const(1)', 1, 2)
        checker.check_children('Const(1)', ['1'])
        checker.check_region('Add', 0, len(source) - 1)
        checker.check_children(
            'Add', ['(', 'Const(1)', ') ', '+', ' ', 'Const(2)'])

    def test_basic_opening_biway(self):
        source = '(1) + (2)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Add', 0, len(source) - 1)
        checker.check_children(
            'Add', ['(', 'Const(1)', ') ', '+', ' (', 'Const(2)', ')'])

    def test_basic_opening_double(self):
        source = '1 + ((2))\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Add', 0, len(source) - 1)
        checker.check_children(
            'Add', ['Const(1)', ' ', '+', ' ((', 'Const(2)', ')', ')'])

    def test_handling_comments(self):
        source = '(1 + #(\n2)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Add', ['Const(1)', ' ', '+', ' #(\n', 'Const(2)'])

    def test_handling_strings(self):
        source = '1 + "("\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Add', ['Const(1)', ' ', '+', ' ', 'Const'])

    def test_handling_implicit_string_concatenation(self):
        source = "a = '1''2'"
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Assign', ['AssName' , ' ', '=', ' ', "Const('12')"])
        checker.check_children('Const', ["'1''2'"])

    def test_handling_implicit_string_concatenation_line_breaks(self):
        source = "a = '1' \\\n'2'"
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Assign', ['AssName' , ' ', '=', ' ', "Const('12')"])
        checker.check_children('Const', ["'1' \\\n'2'"])

    def test_long_integer_literals(self):
        source = "0x1L + a"
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Add', ['Const' , ' ', '+', ' ', 'Name'])
        checker.check_children('Const', ['0x1L'])

    def test_complex_number_literals(self):
        source = "1.0e2j + a"
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Add', ['Const' , ' ', '+', ' ', 'Name'])
        checker.check_children('Const', ['1.0e2j'])

    def test_ass_attr_node(self):
        source = 'a.b = 1\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('AssAttr', 0, source.index('=') - 1)
        checker.check_children('AssAttr', ['Name', '', '.', '', 'b'])

    def test_ass_list_node(self):
        source = '[a, b] = 1, 2\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('AssList', 0, source.index(']') + 1)
        checker.check_children('AssList', ['[', '', 'AssName', '', ',',
                                           ' ', 'AssName', '', ']'])

    def test_ass_tuple(self):
        source = 'a, b = 1, 2\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('AssTuple', 0, source.index('=') - 1)
        checker.check_children(
            'AssTuple', ['AssName', '', ',', ' ', 'AssName'])

    def test_ass_tuple2(self):
        source = '(a, b) = 1, 2\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('AssTuple', 1, source.index('=') - 2)
        checker.check_children(
            'AssTuple', ['AssName', '', ',', ' ', 'AssName'])

    def test_assert(self):
        source = 'assert True\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Assert', 0, len(source) - 1)
        checker.check_children(
            'Assert', ['assert', ' ', 'Name'])

    def test_assert2(self):
        source = 'assert True, "error"\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Assert', 0, len(source) - 1)
        checker.check_children(
            'Assert', ['assert', ' ', 'Name', '', ',', ' ', 'Const'])

    def test_aug_assign_node(self):
        source = 'a += 1\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        start = source.index('a')
        checker.check_region('AugAssign', 0, len(source) - 1)
        checker.check_children(
            'AugAssign', ['Name', ' ', '+=', ' ', 'Const'])

    def test_back_quotenode(self):
        source = '`1`\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Backquote', 0, len(source) - 1)
        checker.check_children(
            'Backquote', ['`', '', 'Const(1)', '', '`'])

    def test_bitand(self):
        source = '1 & 2\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Bitand', 0, len(source) - 1)
        checker.check_children(
            'Bitand', ['Const(1)', ' ', '&', ' ', 'Const(2)'])

    def test_bitor(self):
        source = '1 | 2\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Bitor', 0, len(source) - 1)
        checker.check_children(
            'Bitor', ['Const(1)', ' ', '|', ' ', 'Const(2)'])

    def test_call_func(self):
        source = 'f(1, 2)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('CallFunc', 0, len(source) - 1)
        checker.check_children(
            'CallFunc', ['Name', '', '(', '', 'Const(1)', '', ',',
                         ' ', 'Const(2)', '', ')'])

    def test_call_func_and_keywords(self):
        source = 'f(1, p=2)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'CallFunc', ['Name', '', '(', '', 'Const(1)', '', ',',
                         ' ', 'Keyword', '', ')'])

    def test_call_func_and_start_args(self):
        source = 'f(1, *args)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'CallFunc', ['Name', '', '(', '', 'Const(1)', '', ',',
                         ' ', '*', '', 'Name', '', ')'])

    def test_class_node(self):
        source = 'class A(object):\n    """class docs"""\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Class', 0, len(source) - 1)
        checker.check_children(
            'Class', ['class', ' ', 'A', '', '(', '', 'Name', '', ')',
                      '', ':', '\n    ', '"""class docs"""', '\n    ', 'Stmt'])

    def test_class_with_no_bases(self):
        source = 'class A:\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Class', 0, len(source) - 1)
        checker.check_children(
            'Class', ['class', ' ', 'A', '', ':', '\n    ', 'Stmt'])

    def test_simple_compare(self):
        source = '1 < 2\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Compare', 0, len(source) - 1)
        checker.check_children(
            'Compare', ['Const(1)', ' ', '<', ' ', 'Const(2)'])

    def test_multiple_compare(self):
        source = '1 < 2 <= 3\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Compare', 0, len(source) - 1)
        checker.check_children(
            'Compare', ['Const(1)', ' ', '<', ' ', 'Const(2)', ' ',
                        '<=', ' ', 'Const(3)'])

    def test_decorators_node(self):
        source = '@d\ndef f():\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Decorator', 0, 2)
        checker.check_children('Decorator', ['@', '', 'Name'])

    def test_function_node(self):
        source = 'def f():\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Function', 0, len(source) - 1)
        checker.check_children('Function', ['def', ' ', 'f', '', '(', '',
                                            ')', '', ':', '\n    ', 'Stmt'])

    def test_function_node2(self):
        source = 'def f(p1, **p2):\n    """docs"""\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Function', 0, len(source) - 1)
        checker.check_children(
            'Function', ['def', ' ', 'f', '', '(', '', 'p1', '', ',',
                         ' ', '**', '', 'p2', '', ')', '', ':', '\n    ',
                         '"""docs"""', '\n    ', 'Stmt'])

    def test_dict_node(self):
        source = '{1: 2, 3: 4}\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Dict', 0, len(source) - 1)
        checker.check_children(
            'Dict', ['{', '', 'Const(1)', '', ':', ' ', 'Const(2)', '', ',',
                     ' ', 'Const(3)', '', ':', ' ', 'Const(4)', '', '}'])

    def test_div_node(self):
        source = '1 / 2\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Div', 0, len(source) - 1)
        checker.check_children('Div', ['Const(1)', ' ', '/', ' ', 'Const(2)'])

    def test_simple_exec_node(self):
        source = 'exec ""\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Exec', 0, len(source) - 1)
        checker.check_children('Exec', ['exec', ' ', 'Const'])

    def test_exec_node(self):
        source = 'exec "" in locals(), globals()\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Exec', 0, len(source) - 1)
        checker.check_children(
            'Exec', ['exec', ' ', 'Const', ' ', 'in',
                     ' ', 'CallFunc', '', ',', ' ', 'CallFunc'])

    def test_for_node(self):
        source = 'for i in range(1):\n    pass\nelse:\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('For', 0, len(source) - 1)
        checker.check_children(
            'For', ['for', ' ', 'AssName', ' ', 'in', ' ', 'CallFunc', '',
                    ':', '\n    ', 'Stmt', '\n',
                    'else', '', ':', '\n    ', 'Stmt'])

    def test_normal_from_node(self):
        source = 'from x import y\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('From', 0, len(source) - 1)
        checker.check_children(
            'From', ['from', ' ', 'x', ' ', 'import', ' ', 'y'])

    def test_from_node(self):
        source = 'from ..x import y as z\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('From', 0, len(source) - 1)
        checker.check_children(
            'From', ['from', ' ', '..', '', 'x', ' ', 'import', ' ', 'y',
                     ' ', 'as', ' ', 'z'])


class _ResultChecker(object):

    def __init__(self, test_case, ast):
        self.test_case = test_case
        self.ast = ast

    def check_region(self, text, start, end):
        node = self._find_node(text)
        self.test_case.assertEquals((start, end), node.region)

    def _find_node(self, text):
        class Search(object):
            result = None
            def __call__(self, node):
                if repr(node).startswith(text):
                    self.result = node
                return self.result is not None
        search = Search()
        patchedast.call_for_nodes(self.ast, search, recursive=True)
        return search.result

    def check_children(self, text, children):
        node = self._find_node(text)
        try:
            result = list(node.sorted_children)
        except:
            raise
        self.test_case.assertEquals(len(children), len(result))
        for expected, child in zip(children, result):
            if isinstance(child, basestring):
                self.test_case.assertEquals(expected, child)
            else:
                self.test_case.assertTrue(repr(child).startswith(expected))


if __name__ == '__main__':
    unittest.main()
