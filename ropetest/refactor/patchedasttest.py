import unittest

from rope.refactor import patchedast
from ropetest import testutils


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
            'Add', ['Const(1)', ' ', '+', ' ((', 'Const(2)', '))'])

    def test_handling_comments(self):
        source = '(1 + #(\n2)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Add', ['Const(1)', ' ', '+', ' #(\n', 'Const(2)'])

    def test_handling_parens_with_spaces(self):
        source = '1 + (2\n    )\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Add', ['Const(1)', ' ', '+', ' (', 'Const(2)', '\n    )'])

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
        checker.check_region('AssTuple', 0, source.index('=') - 1)
        checker.check_children(
            'AssTuple', ['(', '', 'AssName', '', ',', ' ', 'AssName', '', ')'])

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

    def test_call_func_and_only_dstart_args(self):
        source = 'f(**kwds)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'CallFunc', ['Name', '', '(', '', '**', '', 'Name', '', ')'])

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

    @testutils.run_only_for_25
    def test_from_node(self):
        source = 'from ..x import y as z\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('From', 0, len(source) - 1)
        checker.check_children(
            'From', ['from', ' ', '..', '', 'x', ' ', 'import', ' ', 'y',
                     ' ', 'as', ' ', 'z'])

    def test_simple_gen_expr_node(self):
        source = 'zip(i for i in x)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('GenExpr', 4, len(source) - 2)
        checker.check_children(
            'GenExprInner', ['Name', ' ', 'GenExprFor'])
        checker.check_children(
            'GenExprFor', ['for', ' ', 'AssName', ' ', 'in', ' ', 'Name'])

    def test_gen_expr_node_handling_surrounding_parens(self):
        source = '(i for i in x)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('GenExpr', 0, len(source) - 1)
        checker.check_children(
            'GenExpr', ['(', '', 'GenExprInner', '', ')'])

    def test_gen_expr_node2(self):
        source = 'zip(i for i in range(1) if i == 1)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'GenExprFor', ['for', ' ', 'AssName', ' ', 'in', ' ', 'CallFunc',
                           ' ', 'GenExprIf'])
        checker.check_children('GenExprIf', ['if', ' ', 'Compare'])

    def test_get_attr_node(self):
        source = 'a.b\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Getattr', 0, len(source) - 1)
        checker.check_children('Getattr', ['Name', '', '.', '', 'b'])

    def test_global_node(self):
        source = 'global a, b\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Global', 0, len(source) - 1)
        checker.check_children('Global', ['global', ' ', 'a', '', ',', ' ', 'b'])

    def test_if_node(self):
        source = 'if True:\n    pass\nelse:\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('If', 0, len(source) - 1)
        checker.check_children(
            'If', ['if', ' ', 'Name', '', ':', '\n    ', 'Stmt', '\n',
                   'else', '', ':', '\n    ', 'Stmt'])

    def test_if_node2(self):
        source = 'if True:\n    pass\nelif False:\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('If', 0, len(source) - 1)
        checker.check_children(
            'If', ['if', ' ', 'Name', '', ':', '\n    ', 'Stmt', '\n',
                   'elif', ' ', 'Name', '', ':', '\n    ', 'Stmt'])

    def test_import_node(self):
        source = 'import a, b as c\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Import', 0, len(source) - 1)
        checker.check_children(
            'Import', ['import', ' ', 'a', '', ',', ' ', 'b', ' ',
                       'as', ' ', 'c'])

    def test_lambda_node(self):
        source = 'lambda a, b=1, *z: None\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Lambda', 0, len(source) - 1)
        checker.check_children(
            'Lambda', ['lambda', ' ', 'a', '', ',', ' ', 'b', '', '=', '',
                       'Const(1)', '', ',', ' ', '*', '', 'z', '', ':',
                       ' ', 'Name'])

    def test_list_node(self):
        source = '[1, 2]\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('List', 0, len(source) - 1)
        checker.check_children(
            'List', ['[', '', 'Const(1)', '', ',', ' ', 'Const(2)', '', ']'])

    def test_list_comp_node(self):
        source = '[i for i in range(1) if True]\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('ListComp', 0, len(source) - 1)
        checker.check_children(
            'ListComp', ['[', '', 'Name', ' ', 'ListCompFor', '', ']'])
        checker.check_children(
            'ListCompFor', ['for', ' ', 'AssName', ' ', 'in', ' ',
                            'CallFunc', ' ', 'ListCompIf'])
        checker.check_children('ListCompIf', ['if', ' ', 'Name'])

    def test_simple_module_node(self):
        source = 'pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Module', 0, len(source))
        checker.check_children('Module', ['', 'Stmt', '\n'])

    def test_module_node(self):
        source = '"""docs"""\npass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Module', 0, len(source))
        checker.check_children('Module', ['', '"""docs"""', '\n', 'Stmt', '\n'])

    def test_not_and_or_nodes(self):
        source = 'not True or False\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children('Discard', ['Or'])
        checker.check_children('Or', ['Not', ' ', 'or', ' ', 'Name'])

    def test_print_node(self):
        source = 'print >>out, 1,\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Print', 0, len(source) - 1)
        checker.check_children('Print', ['print', ' ', '>>', '', 'Name', '',
                                         ',', ' ', 'Const(1)', '', ','])

    def test_printnl_node(self):
        source = 'print 1\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Printnl', 0, len(source) - 1)
        checker.check_children('Printnl', ['print', ' ', 'Const(1)'])

    def test_raise_node(self):
        source = 'raise x, y, z\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_region('Raise', 0, len(source) - 1)
        checker.check_children(
            'Raise', ['raise', ' ', 'Name', '', ',', ' ', 'Name', '', ',',
                      ' ', 'Name'])

    def test_return_node(self):
        source = 'def f():\n    return None\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children('Return', ['return', ' ', 'Name'])

    def test_empty_return_node(self):
        source = 'def f():\n    return\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children('Return', ['return'])

    def test_simple_slice_node(self):
        source = 'a[1:2]\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Slice', ['Name', '', '[', '', 'Const(1)', '', ':', '',
                      'Const(2)', '', ']'])

    def test_slice_node2(self):
        source = 'a[:]\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children('Slice', ['Name', '', '[', '', ':', '', ']'])

    def test_simple_subscript(self):
        source = 'a[1]\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Subscript', ['Name', '', '[', '', 'Const(1)', '', ']'])

    def test_tuple_node(self):
        source = '(1, 2)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'Tuple', ['(', '', 'Const(1)', '', ',', ' ', 'Const(2)', '', ')'])

    def test_one_item_tuple_node(self):
        source = '(1,)\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children('Tuple', ['(', '', 'Const(1)', ',', ')'])

    def test_yield_node(self):
        source = 'def f():\n    yield None\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children('Yield', ['yield', ' ', 'Name'])

    def test_while_node(self):
        source = 'while True:\n    pass\nelse:\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'While', ['while', ' ', 'Name', '', ':', '\n    ', 'Stmt', '\n',
                      'else', '', ':', '\n    ', 'Stmt'])

    @testutils.run_only_for_25
    def test_with_node(self):
        source = 'from __future__ import with_statement\nwith a as b:\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'With', ['with', ' ', 'Name', ' ', 'as', ' ', 'AssName', '', ':',
                     '\n    ', 'Stmt'])

    def test_try_finally_node(self):
        source = 'try:\n    pass\nfinally:\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'TryFinally', ['try', '', ':', '\n    ', 'Stmt', '\n', 'finally',
                           '', ':', '\n    ', 'Stmt'])

    def test_try_except_node(self):
        source = 'try:\n    pass\nexcept Exception, e:\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'TryExcept', ['try', '', ':', '\n    ', 'Stmt', '\n', 'except',
                          ' ', 'Name', '', ',', ' ', 'AssName', '', ':',
                          '\n    ', 'Stmt'])

    @testutils.run_only_for_25
    def test_try_except_and_finally_node(self):
        source = 'try:\n    pass\nexcept:\n    pass\nfinally:\n    pass\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        checker.check_children(
            'TryFinally', ['TryExcept', '\n', 'finally',
                           '', ':', '\n    ', 'Stmt'])

    def test_ignoring_comments(self):
        source = '#1\n1\n'
        ast = patchedast.get_patched_ast(source)
        checker = _ResultChecker(self, ast)
        start = source.rindex('1')
        checker.check_region('Const(1)', start, start + 1)


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
        result = list(node.sorted_children)
        self.test_case.assertEquals(len(children), len(result))
        for expected, child in zip(children, result):
            if isinstance(child, basestring):
                self.test_case.assertEquals(expected, child)
            else:
                self.test_case.assertTrue(repr(child).startswith(expected))


if __name__ == '__main__':
    unittest.main()
