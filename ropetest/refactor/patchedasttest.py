import unittest

from rope.base import ast
from rope.refactor import patchedast
from ropetest import testutils


class PatchedASTTest(unittest.TestCase):

    def setUp(self):
        super(PatchedASTTest, self).setUp()

    def tearDown(self):
        super(PatchedASTTest, self).tearDown()

    def test_integer_literals_and_region(self):
        source = 'a = 10\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index('10')
        checker.check_region('Num', start, start + 2)

    def test_integer_literals_and_sorted_children(self):
        source = 'a = 10\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        #start = source.index('10')
        checker.check_children('Num', ['10'])

    def test_ass_name_node(self):
        source = 'a = 10\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index('a')
        checker.check_region('Name', start, start + 1)
        checker.check_children('Name', ['a'])

    def test_assign_node(self):
        source = 'a = 10\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index('a')  # noqa
        checker.check_region('Assign', 0, len(source) - 1)
        checker.check_children(
            'Assign', ['Name', ' ', '=', ' ', 'Num'])

    def test_add_node(self):
        source = '1 + 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('BinOp', 0, len(source) - 1)
        checker.check_children(
            'BinOp', ['Num', ' ', '+', ' ', 'Num'])

    def test_lshift_node(self):
        source = '1 << 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('BinOp', 0, len(source) - 1)
        checker.check_children(
            'BinOp', ['Num', ' ', '<<', ' ', 'Num'])

    def test_and_node(self):
        source = 'True and True\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('BoolOp', 0, len(source) - 1)
        checker.check_children(
            'BoolOp', ['Name', ' ', 'and', ' ', 'Name'])

    def test_basic_closing_parens(self):
        source = '1 + (2)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('BinOp', 0, len(source) - 1)
        checker.check_children(
            'BinOp', ['Num', ' ', '+', ' (', 'Num', ')'])

    def test_basic_opening_parens(self):
        source = '(1) + 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('BinOp', 0, len(source) - 1)
        checker.check_children(
            'BinOp', ['(', 'Num', ') ', '+', ' ', 'Num'])

    def test_basic_opening_biway(self):
        source = '(1) + (2)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('BinOp', 0, len(source) - 1)
        checker.check_children(
            'BinOp', ['(', 'Num', ') ', '+', ' (', 'Num', ')'])

    def test_basic_opening_double(self):
        source = '1 + ((2))\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('BinOp', 0, len(source) - 1)
        checker.check_children(
            'BinOp', ['Num', ' ', '+', ' ((', 'Num', '))'])

    def test_handling_comments(self):
        source = '(1 + #(\n2)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'BinOp', ['Num', ' ', '+', ' #(\n', 'Num'])

    def test_handling_parens_with_spaces(self):
        source = '1 + (2\n    )\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'BinOp', ['Num', ' ', '+', ' (', 'Num', '\n    )'])

    def test_handling_strings(self):
        source = '1 + "("\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'BinOp', ['Num', ' ', '+', ' ', 'Str'])

    def test_handling_implicit_string_concatenation(self):
        source = "a = '1''2'"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Assign', ['Name', ' ', '=', ' ', 'Str'])
        checker.check_children('Str', ["'1''2'"])

    def test_handling_implicit_string_concatenation_line_breaks(self):
        source = "a = '1' \\\n'2'"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Assign', ['Name', ' ', '=', ' ', 'Str'])
        checker.check_children('Str', ["'1' \\\n'2'"])

    def test_handling_explicit_string_concatenation_line_breaks(self):
        source = "a = ('1' \n'2')"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Assign', ['Name', ' ', '=', ' (', 'Str', ')'])
        checker.check_children('Str', ["'1' \n'2'"])

    def test_not_concatenating_strings_on_separate_lines(self):
        source = "'1'\n'2'\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children('Module', ['', 'Expr', '\n', 'Expr', '\n'])

    def test_long_integer_literals(self):
        source = "0x1L + a"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'BinOp', ['Num', ' ', '+', ' ', 'Name'])
        checker.check_children('Num', ['0x1L'])

    def test_complex_number_literals(self):
        source = "1.0e2j + a"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'BinOp', ['Num', ' ', '+', ' ', 'Name'])
        checker.check_children('Num', ['1.0e2j'])

    def test_ass_attr_node(self):
        source = 'a.b = 1\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Attribute', 0, source.index('=') - 1)
        checker.check_children('Attribute', ['Name', '', '.', '', 'b'])

    def test_ass_list_node(self):
        source = '[a, b] = 1, 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('List', 0, source.index(']') + 1)
        checker.check_children('List', ['[', '', 'Name', '', ',',
                                        ' ', 'Name', '', ']'])

    def test_ass_tuple(self):
        source = 'a, b = range(2)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Tuple', 0, source.index('=') - 1)
        checker.check_children(
            'Tuple', ['Name', '', ',', ' ', 'Name'])

    def test_ass_tuple2(self):
        source = '(a, b) = range(2)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Tuple', 0, source.index('=') - 1)
        checker.check_children(
            'Tuple', ['(', '', 'Name', '', ',', ' ', 'Name', '', ')'])

    def test_assert(self):
        source = 'assert True\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Assert', 0, len(source) - 1)
        checker.check_children(
            'Assert', ['assert', ' ', 'Name'])

    def test_assert2(self):
        source = 'assert True, "error"\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Assert', 0, len(source) - 1)
        checker.check_children(
            'Assert', ['assert', ' ', 'Name', '', ',', ' ', 'Str'])

    def test_aug_assign_node(self):
        source = 'a += 1\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index('a')  # noqa
        checker.check_region('AugAssign', 0, len(source) - 1)
        checker.check_children(
            'AugAssign', ['Name', ' ', '+', '', '=', ' ', 'Num'])

    def test_back_quotenode(self):
        source = '`1`\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Repr', 0, len(source) - 1)
        checker.check_children(
            'Repr', ['`', '', 'Num', '', '`'])

    def test_bitand(self):
        source = '1 & 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('BinOp', 0, len(source) - 1)
        checker.check_children(
            'BinOp', ['Num', ' ', '&', ' ', 'Num'])

    def test_bitor(self):
        source = '1 | 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'BinOp', ['Num', ' ', '|', ' ', 'Num'])

    def test_call_func(self):
        source = 'f(1, 2)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Call', 0, len(source) - 1)
        checker.check_children(
            'Call', ['Name', '', '(', '', 'Num', '', ',',
                     ' ', 'Num', '', ')'])

    def test_call_func_and_keywords(self):
        source = 'f(1, p=2)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Call', ['Name', '', '(', '', 'Num', '', ',',
                     ' ', 'keyword', '', ')'])

    def test_call_func_and_start_args(self):
        source = 'f(1, *args)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Call', ['Name', '', '(', '', 'Num', '', ',',
                     ' ', '*', '', 'Name', '', ')'])

    def test_call_func_and_only_dstart_args(self):
        source = 'f(**kwds)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Call', ['Name', '', '(', '', '**', '', 'Name', '', ')'])

    def test_call_func_and_both_varargs_and_kwargs(self):
        source = 'f(*args, **kwds)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Call', ['Name', '', '(', '', '*', '', 'Name', '', ',',
                     ' ', '**', '', 'Name', '', ')'])

    def test_class_node(self):
        source = 'class A(object):\n    """class docs"""\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Class', 0, len(source) - 1)
        checker.check_children(
            'Class', ['class', ' ', 'A', '', '(', '', 'Name', '', ')',
                      '', ':', '\n    ', 'Expr', '\n    ', 'Pass'])

    def test_class_with_no_bases(self):
        source = 'class A:\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Class', 0, len(source) - 1)
        checker.check_children(
            'Class', ['class', ' ', 'A', '', ':', '\n    ', 'Pass'])

    def test_simple_compare(self):
        source = '1 < 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Compare', 0, len(source) - 1)
        checker.check_children(
            'Compare', ['Num', ' ', '<', ' ', 'Num'])

    def test_multiple_compare(self):
        source = '1 < 2 <= 3\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Compare', 0, len(source) - 1)
        checker.check_children(
            'Compare', ['Num', ' ', '<', ' ', 'Num', ' ',
                        '<=', ' ', 'Num'])

    def test_decorators_node(self):
        source = '@d\ndef f():\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('FunctionDef', 0, len(source) - 1)
        checker.check_children(
            'FunctionDef',
            ['@', '', 'Name', '\n', 'def', ' ', 'f', '', '(', '', 'arguments',
             '', ')', '', ':', '\n    ', 'Pass'])

    @testutils.only_for('2.6')
    def test_decorators_for_classes(self):
        source = '@d\nclass C(object):\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('ClassDef', 0, len(source) - 1)
        checker.check_children(
            'ClassDef',
            ['@', '', 'Name', '\n', 'class', ' ', 'C', '', '(', '', 'Name',
             '', ')', '', ':', '\n    ', 'Pass'])

    def test_both_varargs_and_kwargs(self):
        source = 'def f(*args, **kwds):\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'arguments', ['*', '', 'args', '', ',', ' ', '**', '', 'kwds'])

    def test_function_node(self):
        source = 'def f():\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Function', 0, len(source) - 1)
        checker.check_children('Function',
                               ['def', ' ', 'f', '', '(', '', 'arguments', '',
                                            ')', '', ':', '\n    ', 'Pass'])

    def test_function_node2(self):
        source = 'def f(p1, **p2):\n    """docs"""\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Function', 0, len(source) - 1)
        checker.check_children(
            'Function', ['def', ' ', 'f', '', '(', '', 'arguments',
                         '', ')', '', ':', '\n    ', 'Expr', '\n    ',
                         'Pass'])
        checker.check_children(
            'arguments', ['Name', '', ',',
                          ' ', '**', '', 'p2'])

    def test_function_node_and_tuple_parameters(self):
        source = 'def f(a, (b, c)):\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Function', 0, len(source) - 1)
        checker.check_children(
            'Function', ['def', ' ', 'f', '', '(', '', 'arguments',
                         '', ')', '', ':', '\n    ', 'Pass'])
        checker.check_children(
            'arguments', ['Name', '', ',', ' ', 'Tuple'])

    def test_dict_node(self):
        source = '{1: 2, 3: 4}\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Dict', 0, len(source) - 1)
        checker.check_children(
            'Dict', ['{', '', 'Num', '', ':', ' ', 'Num', '', ',',
                     ' ', 'Num', '', ':', ' ', 'Num', '', '}'])

    def test_div_node(self):
        source = '1 / 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('BinOp', 0, len(source) - 1)
        checker.check_children('BinOp', ['Num', ' ', '/', ' ', 'Num'])

    def test_simple_exec_node(self):
        source = 'exec ""\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Exec', 0, len(source) - 1)
        checker.check_children('Exec', ['exec', ' ', 'Str'])

    def test_exec_node(self):
        source = 'exec "" in locals(), globals()\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Exec', 0, len(source) - 1)
        checker.check_children(
            'Exec', ['exec', ' ', 'Str', ' ', 'in',
                     ' ', 'Call', '', ',', ' ', 'Call'])

    def test_for_node(self):
        source = 'for i in range(1):\n    pass\nelse:\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('For', 0, len(source) - 1)
        checker.check_children(
            'For', ['for', ' ', 'Name', ' ', 'in', ' ', 'Call', '',
                    ':', '\n    ', 'Pass', '\n',
                    'else', '', ':', '\n    ', 'Pass'])

    def test_normal_from_node(self):
        source = 'from x import y\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('ImportFrom', 0, len(source) - 1)
        checker.check_children(
            'ImportFrom', ['from', ' ', 'x', ' ', 'import', ' ', 'alias'])
        checker.check_children('alias', ['y'])

    @testutils.run_only_for_25
    def test_from_node(self):
        source = 'from ..x import y as z\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('ImportFrom', 0, len(source) - 1)
        checker.check_children(
            'ImportFrom', ['from', ' ', '..', '', 'x', ' ',
                           'import', ' ', 'alias'])
        checker.check_children('alias', ['y', ' ', 'as', ' ', 'z'])

    @testutils.run_only_for_25
    def test_from_node_relative_import(self):
        source = 'from . import y as z\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('ImportFrom', 0, len(source) - 1)
        checker.check_children(
            'ImportFrom', ['from', ' ', '.', '', '', ' ',
                           'import', ' ', 'alias'])
        checker.check_children('alias', ['y', ' ', 'as', ' ', 'z'])

    def test_simple_gen_expr_node(self):
        source = 'zip(i for i in x)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('GeneratorExp', 4, len(source) - 2)
        checker.check_children(
            'GeneratorExp', ['Name', ' ', 'comprehension'])
        checker.check_children(
            'comprehension', ['for', ' ', 'Name', ' ', 'in', ' ', 'Name'])

    def test_gen_expr_node_handling_surrounding_parens(self):
        source = '(i for i in x)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('GeneratorExp', 0, len(source) - 1)
        checker.check_children(
            'GeneratorExp', ['(', '', 'Name', ' ', 'comprehension', '', ')'])

    def test_gen_expr_node2(self):
        source = 'zip(i for i in range(1) if i == 1)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'comprehension', ['for', ' ', 'Name', ' ', 'in', ' ', 'Call',
                              ' ', 'if', ' ', 'Compare'])

    def test_get_attr_node(self):
        source = 'a.b\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Attribute', 0, len(source) - 1)
        checker.check_children('Attribute', ['Name', '', '.', '', 'b'])

    def test_global_node(self):
        source = 'global a, b\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Global', 0, len(source) - 1)
        checker.check_children('Global', ['global', ' ', 'a', '', ',', ' ',
                               'b'])

    def test_if_node(self):
        source = 'if True:\n    pass\nelse:\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('If', 0, len(source) - 1)
        checker.check_children(
            'If', ['if', ' ', 'Name', '', ':', '\n    ', 'Pass', '\n',
                   'else', '', ':', '\n    ', 'Pass'])

    def test_if_node2(self):
        source = 'if True:\n    pass\nelif False:\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('If', 0, len(source) - 1)
        checker.check_children(
            'If', ['if', ' ', 'Name', '', ':', '\n    ', 'Pass', '\n',
                   'If'])

    def test_if_node3(self):
        source = 'if True:\n    pass\nelse:\n' \
                 '    if True:\n        pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('If', 0, len(source) - 1)
        checker.check_children(
            'If', ['if', ' ', 'Name', '', ':', '\n    ', 'Pass', '\n',
                   'else', '', ':', '\n    ', 'If'])

    def test_import_node(self):
        source = 'import a, b as c\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Import', 0, len(source) - 1)
        checker.check_children(
            'Import', ['import', ' ', 'alias', '', ',', ' ', 'alias'])

    def test_lambda_node(self):
        source = 'lambda a, b=1, *z: None\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Lambda', 0, len(source) - 1)
        checker.check_children(
            'Lambda', ['lambda', ' ', 'arguments', '', ':', ' ', 'Name'])
        checker.check_children(
            'arguments', ['Name', '', ',', ' ', 'Name', '', '=', '',
                          'Num', '', ',', ' ', '*', '', 'z'])

    def test_list_node(self):
        source = '[1, 2]\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('List', 0, len(source) - 1)
        checker.check_children(
            'List', ['[', '', 'Num', '', ',', ' ', 'Num', '', ']'])

    def test_list_comp_node(self):
        source = '[i for i in range(1) if True]\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('ListComp', 0, len(source) - 1)
        checker.check_children(
            'ListComp', ['[', '', 'Name', ' ', 'comprehension', '', ']'])
        checker.check_children(
            'comprehension', ['for', ' ', 'Name', ' ', 'in', ' ',
                              'Call', ' ', 'if', ' ', 'Name'])

    def test_list_comp_node_with_multiple_comprehensions(self):
        source = '[i for i in range(1) for j in range(1) if True]\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('ListComp', 0, len(source) - 1)
        checker.check_children(
            'ListComp', ['[', '', 'Name', ' ', 'comprehension',
                         ' ', 'comprehension', '', ']'])
        checker.check_children(
            'comprehension', ['for', ' ', 'Name', ' ', 'in', ' ',
                              'Call', ' ', 'if', ' ', 'Name'])

    def test_ext_slice_node(self):
        source = 'x = xs[0,:]\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('ExtSlice', 7, len(source) - 2)
        checker.check_children('ExtSlice', ['Index', '', ',', '', 'Slice'])

    def test_simple_module_node(self):
        source = 'pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Module', 0, len(source))
        checker.check_children('Module', ['', 'Pass', '\n'])

    def test_module_node(self):
        source = '"""docs"""\npass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Module', 0, len(source))
        checker.check_children('Module', ['', 'Expr', '\n', 'Pass', '\n'])
        checker.check_children('Str', ['"""docs"""'])

    def test_not_and_or_nodes(self):
        source = 'not True or False\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children('Expr', ['BoolOp'])
        checker.check_children('BoolOp', ['UnaryOp', ' ', 'or', ' ', 'Name'])

    def test_print_node(self):
        source = 'print >>out, 1,\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Print', 0, len(source) - 1)
        checker.check_children('Print', ['print', ' ', '>>', '', 'Name', '',
                                         ',', ' ', 'Num', '', ','])

    def test_printnl_node(self):
        source = 'print 1\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Print', 0, len(source) - 1)
        checker.check_children('Print', ['print', ' ', 'Num'])

    def test_raise_node(self):
        source = 'raise x, y, z\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region('Raise', 0, len(source) - 1)
        checker.check_children(
            'Raise', ['raise', ' ', 'Name', '', ',', ' ', 'Name', '', ',',
                      ' ', 'Name'])

    def test_return_node(self):
        source = 'def f():\n    return None\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children('Return', ['return', ' ', 'Name'])

    def test_empty_return_node(self):
        source = 'def f():\n    return\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children('Return', ['return'])

    def test_simple_slice_node(self):
        source = 'a[1:2]\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Subscript', ['Name', '', '[', '', 'Slice', '', ']'])
        checker.check_children(
            'Slice', ['Num', '', ':', '', 'Num'])

    def test_slice_node2(self):
        source = 'a[:]\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children('Subscript', ['Name', '', '[', '', 'Slice',
                               '', ']'])
        checker.check_children('Slice', [':'])

    def test_simple_subscript(self):
        source = 'a[1]\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Subscript', ['Name', '', '[', '', 'Index', '', ']'])
        checker.check_children('Index', ['Num'])

    def test_tuple_node(self):
        source = '(1, 2)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Tuple', ['(', '', 'Num', '', ',', ' ', 'Num', '', ')'])

    def test_tuple_node2(self):
        source = '#(\n1, 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children('Tuple', ['Num', '', ',', ' ', 'Num'])

    def test_one_item_tuple_node(self):
        source = '(1,)\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children('Tuple', ['(', '', 'Num', ',', ')'])

    def test_empty_tuple_node(self):
        source = '()\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children('Tuple', ['(', '', ')'])

    def test_yield_node(self):
        source = 'def f():\n    yield None\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children('Yield', ['yield', ' ', 'Name'])

    def test_while_node(self):
        source = 'while True:\n    pass\nelse:\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'While', ['while', ' ', 'Name', '', ':', '\n    ', 'Pass', '\n',
                      'else', '', ':', '\n    ', 'Pass'])

    @testutils.run_only_for_25
    def test_with_node(self):
        source = 'from __future__ import with_statement\nwith a as ' \
            'b:\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'With', ['with', ' ', 'Name', ' ', 'as', ' ', 'Name', '', ':',
                     '\n    ', 'Pass'])

    def test_try_finally_node(self):
        source = 'try:\n    pass\nfinally:\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'TryFinally', ['try', '', ':', '\n    ', 'Pass', '\n', 'finally',
                           '', ':', '\n    ', 'Pass'])

    def test_try_except_node(self):
        source = 'try:\n    pass\nexcept Exception, e:\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'TryExcept', ['try', '', ':', '\n    ', 'Pass', '\n',
                          ('excepthandler', 'ExceptHandler')])
        checker.check_children(
            ('excepthandler', 'ExceptHandler'),
            ['except', ' ', 'Name', '', ',', ' ', 'Name', '', ':',
             '\n    ', 'Pass'])

    def test_try_except_node__with_as_syntax(self):
        source = 'try:\n    pass\nexcept Exception as e:\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'TryExcept', ['try', '', ':', '\n    ', 'Pass', '\n',
                          ('excepthandler', 'ExceptHandler')])
        checker.check_children(
            ('excepthandler', 'ExceptHandler'),
            ['except', ' ', 'Name', ' ', 'as', ' ', 'Name', '', ':',
             '\n    ', 'Pass'])

    @testutils.run_only_for_25
    def test_try_except_and_finally_node(self):
        source = 'try:\n    pass\nexcept:\n    pass\nfinally:\n    pass\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'TryFinally', ['TryExcept', '\n', 'finally',
                           '', ':', '\n    ', 'Pass'])

    def test_ignoring_comments(self):
        source = '#1\n1\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.rindex('1')
        checker.check_region('Num', start, start + 1)

    def test_simple_sliceobj(self):
        source = 'a[1::3]\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Slice', ['Num', '', ':', '', ':', '', 'Num'])

    def test_ignoring_strings_that_start_with_a_char(self):
        source = 'r"""("""\n1\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Module', ['', 'Expr', '\n', 'Expr', '\n'])

    def test_how_to_handle_old_not_equals(self):
        source = '1 <> 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Compare', ['Num', ' ', '<>', ' ', 'Num'])

    def test_semicolon(self):
        source = '1;\n'
        patchedast.get_patched_ast(source, True)

    @testutils.run_only_for_25
    def test_if_exp_node(self):
        source = '1 if True else 2\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'IfExp', ['Num', ' ', 'if', ' ', 'Name', ' ', 'else',
                      ' ', 'Num'])

    def test_delete_node(self):
        source = 'del a, b\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            'Delete', ['del', ' ', 'Name', '', ',', ' ', 'Name'])


class _ResultChecker(object):

    def __init__(self, test_case, ast):
        self.test_case = test_case
        self.ast = ast

    def check_region(self, text, start, end):
        node = self._find_node(text)
        if node is None:
            self.test_case.fail('Node <%s> cannot be found' % text)
        self.test_case.assertEquals((start, end), node.region)

    def _find_node(self, text):
        goal = text
        if not isinstance(text, (tuple, list)):
            goal = [text]

        class Search(object):
            result = None

            def __call__(self, node):
                for text in goal:
                    if str(node).startswith(text):
                        self.result = node
                        break
                    if node.__class__.__name__.startswith(text):
                        self.result = node
                        break
                return self.result is not None
        search = Search()
        ast.call_for_nodes(self.ast, search, recursive=True)
        return search.result

    def check_children(self, text, children):
        node = self._find_node(text)
        if node is None:
            self.test_case.fail('Node <%s> cannot be found' % text)
        result = list(node.sorted_children)
        self.test_case.assertEquals(len(children), len(result))
        for expected, child in zip(children, result):
            goals = expected
            if not isinstance(expected, (tuple, list)):
                goals = [expected]
            for goal in goals:
                if goal == '' or isinstance(child, basestring):
                    self.test_case.assertEquals(goal, child)
                    break
            else:
                self.test_case.assertNotEquals(
                    '', text, 'probably ignoring some node')
                self.test_case.assertTrue(
                    child.__class__.__name__.startswith(expected),
                    msg='Expected <%s> but was <%s>' %
                    (expected, child.__class__.__name__))


if __name__ == '__main__':
    unittest.main()
