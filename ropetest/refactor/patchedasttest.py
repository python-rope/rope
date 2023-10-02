import itertools
import sys
import unittest
from textwrap import dedent

from rope.base import ast
from rope.refactor import patchedast
from ropetest import testutils

NameConstant = "Name" if sys.version_info <= (3, 8) else "NameConstant"


class PatchedASTTest(unittest.TestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def assert_single_case_match_block(self, checker, match_type):
        checker.check_children("Match", [
            "match",
            " ",
            "Name",
            "",
            ":",
            "\n    ",
            "match_case",
        ])
        checker.check_children("match_case", [
            "case",
            " ",
            match_type,
            "",
            ":",
            "\n        ",
            "Expr",
        ])

    def test_operator_support_completeness(self):
        ast_ops = {
            n.__name__
            for n in itertools.chain(
                ast.boolop.__subclasses__(),
                ast.cmpop.__subclasses__(),
                ast.operator.__subclasses__(),
                ast.unaryop.__subclasses__(),
            )
        }
        supported_ops = set(patchedast._PatchingASTWalker._operators)
        assert ast_ops == supported_ops

    def test_bytes_string(self):
        source = '1 + b"("\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        str_fragment = 'b"("'
        start = source.index(str_fragment)
        checker.check_region("Bytes", start, start + len(str_fragment))
        checker.check_children("Bytes", [str_fragment])

    def test_integer_literals_and_region(self):
        source = "a = 10\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index("10")
        checker.check_region("Num", start, start + 2)

    def test_negative_integer_literals_and_region(self):
        source = "a = -10\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index("-10") + 1
        end = start + 2
        # Python 3 parses as UnaryOp(op=USub(), operand=Num(n=10))
        checker.check_region("Num", start, end)

    def test_scientific_integer_literals_and_region(self):
        source = "a = -1.0e-3\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index("-1.0e-3") + 1
        end = start + 6
        # Python 3 parses as UnaryOp(op=USub(), operand=Num(n=10))
        checker.check_region("Num", start, end)

    def test_hex_integer_literals_and_region(self):
        source = "a = 0x1\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index("0x1")
        checker.check_region("Num", start, start + 3)

    def test_octal_integer_literals_and_region(self):
        source = "a = -0o1251\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index("-0o1251") + 1
        end = start + 6
        # Python 3 parses as UnaryOp(op=USub(), operand=Num(n=10))
        checker.check_region("Num", start, end)
        checker.check_children("Num", ["0o1251"])

    def test_integer_literals_and_sorted_children(self):
        source = "a = 10\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Num", ["10"])

    def test_ellipsis(self):
        source = "a[...]\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index("...")
        checker.check_region("Ellipsis", start, start + len("..."))

    def test_ass_name_node(self):
        source = "a = 10\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index("a")
        checker.check_region("Name", start, start + 1)
        checker.check_children("Name", ["a"])

    def test_assign_node(self):
        source = "a = 10\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Assign", 0, len(source) - 1)
        checker.check_children("Assign", ["Name", " ", "=", " ", "Num"])

    @testutils.only_for_versions_higher("3.6")
    def test_ann_assign_node_without_target(self):
        source = "a: List[int]\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("AnnAssign", 0, len(source) - 1)
        checker.check_children("AnnAssign", ["Name", "", ":", " ", "Subscript"])

    @testutils.only_for_versions_higher("3.6")
    def test_ann_assign_node_with_target(self):
        source = "a: int = 10\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("AnnAssign", 0, len(source) - 1)
        checker.check_children(
            "AnnAssign", ["Name", "", ":", " ", "Name", " ", "=", " ", "Num"]
        )

    def test_add_node(self):
        source = "1 + 2\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("BinOp", 0, len(source) - 1)
        checker.check_children("BinOp", ["Num", " ", "+", " ", "Num"])

    def test_lshift_node(self):
        source = "1 << 2\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("BinOp", 0, len(source) - 1)
        checker.check_children("BinOp", ["Num", " ", "<<", " ", "Num"])

    def test_and_node(self):
        source = "True and True\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("BoolOp", 0, len(source) - 1)
        checker.check_children("BoolOp", [NameConstant, " ", "and", " ", NameConstant])

    def test_matmult_node(self):
        source = "a @ b\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("BinOp", ["Name", " ", "@", " ", "Name"])

    def test_basic_closing_parens(self):
        source = "1 + (2)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("BinOp", 0, len(source) - 1)
        checker.check_children("BinOp", ["Num", " ", "+", " (", "Num", ")"])

    def test_basic_opening_parens(self):
        source = "(1) + 2\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("BinOp", 0, len(source) - 1)
        checker.check_children("BinOp", ["(", "Num", ") ", "+", " ", "Num"])

    def test_basic_opening_biway(self):
        source = "(1) + (2)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("BinOp", 0, len(source) - 1)
        checker.check_children("BinOp", ["(", "Num", ") ", "+", " (", "Num", ")"])

    def test_basic_opening_double(self):
        source = "1 + ((2))\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("BinOp", 0, len(source) - 1)
        checker.check_children("BinOp", ["Num", " ", "+", " ((", "Num", "))"])

    def test_handling_comments(self):
        source = "(1 + #(\n2)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("BinOp", ["Num", " ", "+", " #(\n", "Num"])

    def test_handling_parens_with_spaces(self):
        source = "1 + (2\n    )\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("BinOp", ["Num", " ", "+", " (", "Num", "\n    )"])

    def test_handling_strings(self):
        source = '1 + "("\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("BinOp", ["Num", " ", "+", " ", "Str"])

    def test_handling_fstrings(self):
        source = '1 + f"("\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("BinOp", ["Num", " ", "+", " ", "JoinedStr"])

    def test_handling_implicit_string_concatenation(self):
        source = "a = '1''2'"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Assign", ["Name", " ", "=", " ", "Str"])
        checker.check_children("Str", ["'1''2'"])

    def test_handling_implicit_string_concatenation_line_breaks(self):
        source = dedent("""\
            a = '1' \\
            '2'""")
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Assign", ["Name", " ", "=", " ", "Str"])
        checker.check_children("Str", ["'1' \\\n'2'"])

    def test_handling_explicit_string_concatenation_line_breaks(self):
        source = "a = ('1' \n'2')"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Assign", ["Name", " ", "=", " (", "Str", ")"])
        checker.check_children("Str", ["'1' \n'2'"])

    def test_not_concatenating_strings_on_separate_lines(self):
        source = dedent("""\
            '1'
            '2'
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Module", ["", "Expr", "\n", "Expr", "\n"])

    def test_handling_raw_strings(self):
        source = 'r"abc"\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Str", ['r"abc"'])

    @testutils.only_for_versions_higher("3.6")
    def test_handling_format_strings_basic(self):
        source = '1 + f"abc{a}"\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("JoinedStr", ['f"', "abc", "FormattedValue", "", '"'])
        checker.check_children("FormattedValue", ["{", "", "Name", "", "}"])

    @testutils.only_for_versions_higher("3.6")
    def test_handling_format_strings_with_implicit_join(self):
        source = '''"1" + rf'abc{a}' f"""xxx{b} """\n'''
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "JoinedStr",
            ["rf'", "abc", "FormattedValue", '\' f"""xxx', "FormattedValue", " ", '"""'],
        )
        checker.check_children("FormattedValue", ["{", "", "Name", "", "}"])

    @testutils.only_for_versions_higher("3.6")
    def test_handling_format_strings_with_format_spec(self):
        source = 'f"abc{a:01}"\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("JoinedStr", ['f"', "abc", "FormattedValue", "", '"'])
        checker.check_children(
            "FormattedValue", ["{", "", "Name", "", ":", "", "01", "", "}"]
        )

    @testutils.only_for_versions_higher("3.6")
    def test_handling_format_strings_with_inner_format_spec(self):
        source = 'f"abc{a:{length}01}"\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("JoinedStr", ['f"', "abc", "FormattedValue", "", '"'])
        checker.check_children(
            "FormattedValue",
            ["{", "", "Name", "", ":", "{", "Name", "}", "01", "", "}"],
        )

    @testutils.only_for_versions_higher("3.6")
    def test_handling_format_strings_with_expression(self):
        source = 'f"abc{a + b}"\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("JoinedStr", ['f"', "abc", "FormattedValue", "", '"'])
        checker.check_children("FormattedValue", ["{", "", "BinOp", "", "}"])

    def test_complex_number_literals(self):
        source = "1.0e2j + a"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("BinOp", ["Num", " ", "+", " ", "Name"])
        checker.check_children("Num", ["1.0e2j"])

    def test_ass_attr_node(self):
        source = "a.b = 1\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Attribute", 0, source.index("=") - 1)
        checker.check_children("Attribute", ["Name", "", ".", "", "b"])

    def test_ass_list_node(self):
        source = "[a, b] = 1, 2\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("List", 0, source.index("]") + 1)
        checker.check_children("List", ["[", "", "Name", "", ",", " ", "Name", "", "]"])

    def test_ass_tuple(self):
        source = "a, b = range(2)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Tuple", 0, source.index("=") - 1)
        checker.check_children("Tuple", ["Name", "", ",", " ", "Name"])

    def test_ass_tuple2(self):
        source = "(a, b) = range(2)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Tuple", 0, source.index("=") - 1)
        checker.check_children(
            "Tuple", ["(", "", "Name", "", ",", " ", "Name", "", ")"]
        )

    def test_assert(self):
        source = "assert True\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Assert", 0, len(source) - 1)
        checker.check_children("Assert", ["assert", " ", NameConstant])

    def test_assert2(self):
        source = 'assert True, "error"\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Assert", 0, len(source) - 1)
        checker.check_children(
            "Assert", ["assert", " ", NameConstant, "", ",", " ", "Str"]
        )

    def test_aug_assign_node(self):
        source = "a += 1\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("AugAssign", 0, len(source) - 1)
        checker.check_children("AugAssign", ["Name", " ", "+", "", "=", " ", "Num"])

    def test_bitand(self):
        source = "1 & 2\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("BinOp", 0, len(source) - 1)
        checker.check_children("BinOp", ["Num", " ", "&", " ", "Num"])

    def test_bitor(self):
        source = "1 | 2\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("BinOp", ["Num", " ", "|", " ", "Num"])

    def test_call_func(self):
        source = "f(1, 2)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Call", 0, len(source) - 1)
        checker.check_children(
            "Call", ["Name", "", "(", "", "Num", "", ",", " ", "Num", "", ")"]
        )

    def test_call_func_and_keywords(self):
        source = "f(1, p=2)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call", ["Name", "", "(", "", "Num", "", ",", " ", "keyword", "", ")"]
        )

    @testutils.only_for_versions_lower("3.5")
    def test_call_func_and_star_args(self):
        source = "f(1, *args)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call", ["Name", "", "(", "", "Num", "", ",", " ", "*", "", "Name", "", ")"]
        )

    def test_call_func_and_star_argspython35(self):
        source = "f(1, *args)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call", ["Name", "", "(", "", "Num", "", ",", " *", "Starred", "", ")"]
        )

    @testutils.only_for_versions_lower("3.5")
    def test_call_func_and_only_dstar_args(self):
        source = "f(**kwds)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Call", ["Name", "", "(", "", "**", "", "Name", "", ")"])

    def test_call_func_and_only_dstar_args_python35(self):
        source = "f(**kwds)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Call", ["Name", "", "(", "**", "keyword", "", ")"])

    @testutils.only_for_versions_lower("3.5")
    def test_call_func_and_both_varargs_and_kwargs(self):
        source = "f(*args, **kwds)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call",
            ["Name", "", "(", "", "*", "", "Name", "", ",", " ", "**", "", "Name", "", ")"],
        )

    def test_call_func_and_both_varargs_and_kwargs_python35(self):
        source = "f(*args, **kwds)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call",
            ["Name", "", "(", "*", "Starred", "", ",", " **", "keyword", "", ")"],
        )

    def test_class_node(self):
        source = dedent('''\
            class A(object):
                """class docs"""
                pass
        ''')
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Class", 0, len(source) - 1)
        checker.check_children(
            "Class",
            ["class", " ", "A", "", "(", "", "Name", "", ")", "", ":", "\n    ", "Expr", "\n    ", "Pass"],
        )

    def test_class_with_no_bases(self):
        source = dedent("""\
            class A:
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Class", 0, len(source) - 1)
        checker.check_children("Class", ["class", " ", "A", "", ":", "\n    ", "Pass"])

    def test_simple_compare(self):
        source = "1 < 2\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Compare", 0, len(source) - 1)
        checker.check_children("Compare", ["Num", " ", "<", " ", "Num"])

    def test_multiple_compare(self):
        source = "1 < 2 <= 3\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Compare", 0, len(source) - 1)
        checker.check_children(
            "Compare", ["Num", " ", "<", " ", "Num", " ", "<=", " ", "Num"]
        )

    def test_decorators_node(self):
        source = dedent("""\
            @d
            def f():
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("FunctionDef", 0, len(source) - 1)
        checker.check_children(
            "FunctionDef",
            ["@", "", "Name", "\n", "def", " ", "f", "", "(", "", "arguments", "", ")", "", ":", "\n    ", "Pass"],
        )

    def test_decorators_for_classes(self):
        source = dedent("""\
            @d
            class C(object):
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("ClassDef", 0, len(source) - 1)
        checker.check_children(
            "ClassDef",
            ["@", "", "Name", "\n", "class", " ", "C", "", "(", "", "Name", "", ")", "", ":", "\n    ", "Pass"],
        )

    def test_both_varargs_and_kwargs(self):
        source = dedent("""\
            def f(*args, **kwds):
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "arguments", ["*", "", "args", "", ",", " ", "**", "", "kwds"]
        )

    def test_function_node(self):
        source = dedent("""\
            def f():
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Function", 0, len(source) - 1)
        checker.check_children(
            "Function",
            ["def", " ", "f", "", "(", "", "arguments", "", ")", "", ":", "\n    ", "Pass"],
        )

    @testutils.only_for_versions_higher("3.5")
    def test_async_function_node(self):
        source = dedent("""\
            async def f():
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("AsyncFunction", 0, len(source) - 1)
        checker.check_children(
            "AsyncFunction",
            ["async", " ", "def", " ", "f", "", "(", "", "arguments", "", ")", "", ":", "\n    ", "Pass"],
        )

    def test_function_node2(self):
        source = dedent('''\
            def f(p1, **p2):
                """docs"""
                pass
        ''')
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Function", 0, len(source) - 1)
        checker.check_children(
            "Function",
            ["def", " ", "f", "", "(", "", "arguments", "", ")", "", ":", "\n    ", "Expr", "\n    ", "Pass"],
        )
        expected_child = ast.arg.__name__
        checker.check_children(
            "arguments", [expected_child, "", ",", " ", "**", "", "p2"]
        )

    def test_dict_node(self):
        source = "{1: 2, 3: 4}\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Dict", 0, len(source) - 1)
        checker.check_children(
            "Dict",
            ["{", "", "Num", "", ":", " ", "Num", "", ",", " ", "Num", "", ":", " ", "Num", "", "}"],
        )

    def test_dict_node_with_unpacking(self):
        source = "{**dict1, **dict2}\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Dict", 0, len(source) - 1)
        checker.check_children(
            "Dict", ["{", "", "**", "", "Name", "", ",", " ", "**", "", "Name", "", "}"]
        )

    def test_div_node(self):
        source = "1 / 2\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("BinOp", 0, len(source) - 1)
        checker.check_children("BinOp", ["Num", " ", "/", " ", "Num"])

    def test_for_node(self):
        source = dedent("""\
            for i in range(1):
                pass
            else:
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("For", 0, len(source) - 1)
        checker.check_children(
            "For",
            ["for", " ", "Name", " ", "in", " ", "Call", "", ":", "\n    ", "Pass", "\n", "else", "", ":", "\n    ", "Pass"],
        )

    @testutils.only_for_versions_higher("3.5")
    def test_async_for_node(self):
        source = dedent("""\
            async def foo():
                async for i in range(1):
                    pass
                else:
                    pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("AsyncFor", source.index("async for"), len(source) - 1)
        checker.check_children(
            "AsyncFor",
            ["async", " ", "for", " ", "Name", " ", "in", " ", "Call", "", ":", "\n        ", "Pass", "\n    ", "else", "", ":", "\n        ", "Pass"],
        )

    @testutils.only_for_versions_higher("3.8")
    def test_named_expr_node(self):
        source = dedent("""\
            if a := 10 == 10:
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.index("a")
        checker.check_region("NamedExpr", start, start + 13)
        checker.check_children("NamedExpr", ["Name", " ", ":=", " ", "Compare"])

    def test_normal_from_node(self):
        source = "from x import y\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("ImportFrom", 0, len(source) - 1)
        checker.check_children(
            "ImportFrom", ["from", " ", "x", " ", "import", " ", "alias"]
        )
        checker.check_children("alias", ["y"])

    def test_from_node(self):
        source = "from ..x import y as z\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("ImportFrom", 0, len(source) - 1)
        checker.check_children(
            "ImportFrom", ["from", " ", ".", "", ".", "", "x", " ", "import", " ", "alias"]
        )
        checker.check_children("alias", ["y", " ", "as", " ", "z"])

    def test_from_node_relative_import(self):
        source = "from . import y as z\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("ImportFrom", 0, len(source) - 1)
        checker.check_children(
            "ImportFrom", ["from", " ", ".", " ", "import", " ", "alias"]
        )
        checker.check_children("alias", ["y", " ", "as", " ", "z"])

    def test_from_node_whitespace_around_dots_1(self):
        source = "from . . . import y as z\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("ImportFrom", 0, len(source) - 1)
        checker.check_children(
            "ImportFrom", ["from", " ", ".", " ", ".", " ", ".", " ", "import", " ", "alias"]
        )
        checker.check_children("alias", ["y", " ", "as", " ", "z"])

    def test_from_node_whitespace_around_dots_2(self):
        source = "from . a . b import y as z\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("ImportFrom", 0, len(source) - 1)
        checker.check_children(
            "ImportFrom", ["from", " ", ".", " ", "a", " . ", "b", " ", "import", " ", "alias"]
        )
        checker.check_children("alias", ["y", " ", "as", " ", "z"])

    def test_simple_gen_expr_node(self):
        source = "zip(i for i in x)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("GeneratorExp", 4, len(source) - 2)
        checker.check_children("GeneratorExp", ["Name", " ", "comprehension"])
        checker.check_children(
            "comprehension", ["for", " ", "Name", " ", "in", " ", "Name"]
        )

    def test_gen_expr_node_handling_surrounding_parens(self):
        source = "(i for i in x)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("GeneratorExp", 0, len(source) - 1)
        checker.check_children(
            "GeneratorExp", ["(", "", "Name", " ", "comprehension", "", ")"]
        )

    def test_gen_expr_node2(self):
        source = "zip(i for i in range(1) if i == 1)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "comprehension",
            ["for", " ", "Name", " ", "in", " ", "Call", " ", "if", " ", "Compare"],
        )

    def test_get_attr_node(self):
        source = "a.b\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Attribute", 0, len(source) - 1)
        checker.check_children("Attribute", ["Name", "", ".", "", "b"])

    def test_global_node(self):
        source = "global a, b\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Global", 0, len(source) - 1)
        checker.check_children("Global", ["global", " ", "a", "", ",", " ", "b"])

    def test_nonlocal_node(self):
        source = "nonlocal a, b\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Nonlocal", 0, len(source) - 1)
        checker.check_children("Nonlocal", ["nonlocal", " ", "a", "", ",", " ", "b"])

    def test_if_node(self):
        source = "if True:\n    pass\nelse:\n    pass\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("If", 0, len(source) - 1)
        checker.check_children(
            "If",
            ["if", " ", NameConstant, "", ":", "\n    ", "Pass", "\n", "else", "", ":", "\n    ", "Pass"],
        )

    def test_if_node2(self):
        source = dedent("""\
            if True:
                pass
            elif False:
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("If", 0, len(source) - 1)
        checker.check_children(
            "If", ["if", " ", NameConstant, "", ":", "\n    ", "Pass", "\n", "If"]
        )

    def test_if_node3(self):
        source = dedent("""\
            if True:
                pass
            else:
                if True:
                    pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("If", 0, len(source) - 1)
        checker.check_children(
            "If",
            ["if", " ", NameConstant, "", ":", "\n    ", "Pass", "\n", "else", "", ":", "\n    ", "If"],
        )

    def test_import_node(self):
        source = "import a, b as c\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Import", 0, len(source) - 1)
        checker.check_children(
            "Import", ["import", " ", "alias", "", ",", " ", "alias"]
        )

    def test_import_node_whitespace_around_dots(self):
        source = "import a . b, b as c\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Import", 0, len(source) - 1)
        checker.check_children(
            "Import", ["import", " ", "alias", "", ",", " ", "alias"]
        )

    def test_lambda_node(self):
        source = "lambda a, b=1, *z: None\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Lambda", 0, len(source) - 1)
        checker.check_children(
            "Lambda", ["lambda", " ", "arguments", "", ":", " ", NameConstant]
        )
        expected_child = ast.arg.__name__
        checker.check_children(
            "arguments",
            [expected_child, "", ",", " ", expected_child, "", "=", "", "Num", "", ",", " ", "*", "", "z"],
        )

    def test_list_node(self):
        source = "[1, 2]\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("List", 0, len(source) - 1)
        checker.check_children("List", ["[", "", "Num", "", ",", " ", "Num", "", "]"])

    def test_list_comp_node(self):
        source = "[i for i in range(1) if True]\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("ListComp", 0, len(source) - 1)
        checker.check_children(
            "ListComp", ["[", "", "Name", " ", "comprehension", "", "]"]
        )
        checker.check_children(
            "comprehension",
            ["for", " ", "Name", " ", "in", " ", "Call", " ", "if", " ", NameConstant],
        )

    def test_list_comp_node_with_multiple_comprehensions(self):
        source = "[i for i in range(1) for j in range(1) if True]\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("ListComp", 0, len(source) - 1)
        checker.check_children(
            "ListComp",
            ["[", "", "Name", " ", "comprehension", " ", "comprehension", "", "]"],
        )
        checker.check_children(
            "comprehension",
            ["for", " ", "Name", " ", "in", " ", "Call", " ", "if", " ", NameConstant],
        )

    def test_set_node(self):
        source = "{1, 2}\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Set", 0, len(source) - 1)
        checker.check_children("Set", ["{", "", "Num", "", ",", " ", "Num", "", "}"])

    def test_set_comp_node(self):
        source = "{i for i in range(1) if True}\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("SetComp", 0, len(source) - 1)
        checker.check_children(
            "SetComp", ["{", "", "Name", " ", "comprehension", "", "}"]
        )
        checker.check_children(
            "comprehension",
            ["for", " ", "Name", " ", "in", " ", "Call", " ", "if", " ", NameConstant],
        )

    def test_dict_comp_node(self):
        source = "{i:i for i in range(1) if True}\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("DictComp", 0, len(source) - 1)
        checker.check_children(
            "DictComp",
            ["{", "", "Name", "", ":", "", "Name", " ", "comprehension", "", "}"],
        )
        checker.check_children(
            "comprehension",
            ["for", " ", "Name", " ", "in", " ", "Call", " ", "if", " ", NameConstant],
        )

    def test_ext_slice_node(self):
        source = "x = xs[0,:]\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        if sys.version_info >= (3, 9):
            checker.check_region("Tuple", 7, len(source) - 2)
            checker.check_children("Tuple", ["Num", "", ",", "", "Slice"])
        else:
            checker.check_region("ExtSlice", 7, len(source) - 2)
            checker.check_children("ExtSlice", ["Index", "", ",", "", "Slice"])

    def test_simple_module_node(self):
        source = "pass\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Module", 0, len(source))
        checker.check_children("Module", ["", "Pass", "\n"])

    def test_module_node(self):
        source = dedent('''\
            """docs"""
            pass
        ''')
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Module", 0, len(source))
        checker.check_children("Module", ["", "Expr", "\n", "Pass", "\n"])
        checker.check_children("Str", ['"""docs"""'])

    def test_not_and_or_nodes(self):
        source = "not True or False\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Expr", ["BoolOp"])
        checker.check_children("BoolOp", ["UnaryOp", " ", "or", " ", NameConstant])

    def test_raise_node_bare(self):
        source = "raise\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Raise", 0, len(source) - 1)
        checker.check_children("Raise", ["raise"])

    def test_raise_node_for_python3(self):
        source = "raise x(y)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Raise", 0, len(source) - 1)
        checker.check_children("Raise", ["raise", " ", "Call"])

    def test_raise_node_for_python3_with_cause(self):
        source = "raise x(y) from e\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_region("Raise", 0, len(source) - 1)
        checker.check_children("Raise", ["raise", " ", "Call", " ", "from", " ", "Name"])

    def test_return_node(self):
        source = dedent("""\
            def f():
                return None
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Return", ["return", " ", NameConstant])

    def test_empty_return_node(self):
        source = dedent("""\
            def f():
                return
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Return", ["return"])

    def test_simple_slice_node(self):
        source = "a[1:2]\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Subscript", ["Name", "", "[", "", "Slice", "", "]"])
        checker.check_children("Slice", ["Num", "", ":", "", "Num"])

    def test_slice_node2(self):
        source = "a[:]\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Subscript", ["Name", "", "[", "", "Slice", "", "]"])
        checker.check_children("Slice", [":"])

    def test_simple_subscript(self):
        source = "a[1]\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        if sys.version_info >= (3, 9):
            checker.check_children("Subscript", ["Name", "", "[", "", "Num", "", "]"])
        else:
            checker.check_children("Subscript", ["Name", "", "[", "", "Index", "", "]"])
            checker.check_children("Index", ["Num"])

    def test_tuple_node(self):
        source = "(1, 2)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Tuple", ["(", "", "Num", "", ",", " ", "Num", "", ")"])

    def test_tuple_node2(self):
        source = "#(\n1, 2\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Tuple", ["Num", "", ",", " ", "Num"])

    def test_tuple_with_complex_parentheses1(self):
        source = "a = ( # (he\n ((((), None))))\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Tuple", ["(", "", "Tuple", "", ",", " ", NameConstant, "", ")"]
        )

    def test_tuple_with_complex_parentheses2(self):
        source = "a = ( # (he\n ((((('a')), ('b')))))\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Tuple", ["(", "", "((", "Str", "))", ",", " (", "Str", ")", "", ")"]
        )

    def test_tuple_with_complex_parentheses3(self):
        source = "a = ((), (([],), []),)"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Tuple", ["(", "", "Tuple", "", ",", " ", "Tuple", ",", ")"]
        )

    def test_one_item_tuple_node(self):
        source = "(1,)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Tuple", ["(", "", "Num", ",", ")"])

    def test_empty_tuple_node(self):
        source = "()\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Tuple", ["()"])

    def test_empty_tuple_node2(self):
        source = "a = ((), None)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Tuple", ["(", "", "Tuple", "", ",", " ", NameConstant, "", ")"]
        )

    def test_empty_tuple_node3(self):
        source = "a = (), None\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Tuple", ["Tuple", "", ",", " ", NameConstant]
        )

    def test_yield_node(self):
        source = dedent("""\
            def f():
                yield None
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Yield", ["yield", " ", NameConstant])

    @testutils.only_for_versions_higher("3.3")
    def test_yield_from_node(self):
        source = dedent("""\
            def f(lst):
                yield from lst
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("YieldFrom", ["yield", " ", "from", " ", "Name"])

    def test_while_node(self):
        source = dedent("""\
            while True:
                pass
            else:
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "While",
            ["while", " ", NameConstant, "", ":", "\n    ", "Pass", "\n", "else", "", ":", "\n    ", "Pass"],
        )

    def test_with_node(self):
        source = dedent("""\
            from __future__ import with_statement
            with a as b:
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "With",
            ["with", " ", "Name", " ", "as", " ", "Name", "", ":", "\n    ", "Pass"],
        )

    def test_async_with_node(self):
        source = dedent("""\
            async def afunc():
                async with a as b:
                    pass\n
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "AsyncWith",
            ["async", " ", "with", " ", "Name", " ", "as", " ", "Name", "", ":", "\n        ", "Pass"],
        )

    def test_try_finally_node(self):
        source = dedent("""\
            try:
                pass
            finally:
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        node_to_test = "Try"
        expected_children = ["try", "", ":", "\n    ", "Pass", "\n", "finally", "", ":", "\n    ", "Pass"]
        checker.check_children(node_to_test, expected_children)

    def test_try_except_node(self):
        source = dedent("""\
            try:
                pass
            except Exception as e:
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        node_to_test = "Try"
        checker.check_children(
            node_to_test,
            ["try", "", ":", "\n    ", "Pass", "\n", ("excepthandler", "ExceptHandler")],
        )
        expected_child = "e"
        checker.check_children(
            ("excepthandler", "ExceptHandler"),
            ["except", " ", "Name", " ", "as", " ", expected_child, "", ":", "\n    ", "Pass"],
        )

    def test_try_except_and_finally_node(self):
        source = dedent("""\
            try:
                pass
            except:
                pass
            finally:
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        node_to_test = "Try"
        expected_children = ["try", "", ":", "\n    ", "Pass", "\n", "ExceptHandler", "\n", "finally", "", ":", "\n    ", "Pass"]
        checker.check_children(node_to_test, expected_children)

    @testutils.only_for_versions_higher("3.11")
    def test_try_except_group_node(self):
        source = dedent("""\
            try:
                pass
            except* (ValueError, IOError) as e:
                pass
            except* ZeroDivisionError as e:
                pass
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "TryStar",
            ["try", "", ":", "\n    ", "Pass", "\n", "ExceptHandler", "\n", "ExceptHandler"],
        )
        expected_child = "e"
        checker.check_children(
            "ExceptHandler",
            ["except", "* ", "Name", " ", "as", " ", expected_child, "", ":", "\n    ", "Pass"],
        )

    def test_ignoring_comments(self):
        source = "#1\n1\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        start = source.rindex("1")
        checker.check_region("Num", start, start + 1)

    def test_simple_sliceobj(self):
        source = "a[1::3]\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Slice", ["Num", "", ":", "", ":", "", "Num"])

    def test_ignoring_strings_that_start_with_a_char(self):
        source = 'r"""("""\n1\n'
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Module", ["", "Expr", "\n", "Expr", "\n"])

    def test_semicolon(self):
        source = "1;\n"
        patchedast.get_patched_ast(source, True)

    def test_if_exp_node(self):
        source = "1 if True else 2\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "IfExp", ["Num", " ", "if", " ", NameConstant, " ", "else", " ", "Num"]
        )

    def test_delete_node(self):
        source = "del a, b\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Delete", ["del", " ", "Name", "", ",", " ", "Name"])

    @testutils.only_for_versions_lower("3.5")
    def test_starargs_before_keywords_legacy(self):
        source = "foo(*args, a=1)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call",
            ["Name", "", "(", "", "*", "", "Name", "", ",", " ", "keyword", "", ")"],
        )

    @testutils.only_for_versions_lower("3.5")
    def test_starargs_in_keywords_legacy(self):
        source = "foo(a=1, *args, b=2)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call",
            ["Name", "", "(", "", "keyword", "", ",", " ", "*", "", "Name", "", ",", " ", "keyword", "", ")"],
        )

    @testutils.only_for_versions_lower("3.5")
    def test_starargs_after_keywords_legacy(self):
        source = "foo(a=1, *args)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call",
            ["Name", "", "(", "", "keyword", "", ",", " ", "*", "", "Name", "", ")"],
        )

    def test_starargs_before_keywords(self):
        source = "foo(*args, a=1)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call", ["Name", "", "(", "*", "Starred", "", ",", " ", "keyword", "", ")"]
        )

    def test_starargs_in_keywords(self):
        source = "foo(a=1, *args, b=2)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call",
            ["Name", "", "(", "", "keyword", "", ",", " *", "Starred", "", ",", " ", "keyword", "", ")"],
        )

    def test_starargs_in_positional(self):
        source = "foo(a, *b, c)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call",
            ["Name", "", "(", "", "Name", "", ",", " *", "Starred", "", ",", " ", "Name", "", ")"],
        )

    def test_starargs_after_keywords(self):
        source = "foo(a=1, *args)\n"
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children(
            "Call", ["Name", "", "(", "", "keyword", "", ",", " *", "Starred", "", ")"]
        )

    @testutils.only_for_versions_higher("3.5")
    def test_await_node(self):
        source = dedent("""\
            async def f():
                await sleep()
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Await", ["await", " ", "Call"])

    @testutils.only_for_versions_higher("3.10")
    def test_match_node_with_constant_match_value(self):
        source = dedent("""\
            match x:
                case 1:
                    print(x)
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        self.assert_single_case_match_block(checker, "MatchValue")
        checker.check_children("MatchValue", [
            "Num"
        ])

    @testutils.only_for_versions_higher("3.10")
    def test_match_node_match_case_with_guard(self):
        source = dedent("""\
            match x:
                case int(n) if x < 10:
                    print(n)
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        checker.check_children("Match", [
            "match",
            " ",
            "Name",
            "",
            ":",
            "\n    ",
            "match_case",
        ])
        checker.check_children("match_case", [
            "case",
            " ",
            "MatchClass",
            " ",
            "if",
            " ",
            "Compare",
            "",
            ":",
            "\n        ",
            "Expr",
        ])

    @testutils.only_for_versions_higher("3.10")
    def test_match_node_with_match_class(self):
        source = dedent("""\
            match x:
                case Foo(1):
                    print(x)
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        self.assert_single_case_match_block(checker, "MatchClass")
        checker.check_children("MatchClass", [
            "Name",
            "",
            "(",
            "",
            "MatchValue",
            "",
            ")",
        ])
        checker.check_children("MatchValue", [
            "Num"
        ])

    @testutils.only_for_versions_higher("3.10")
    def test_match_node_with_wildcard(self):
        source = dedent("""\
            match x:
                case _:
                    print(x)
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        self.assert_single_case_match_block(checker, "MatchAs")
        checker.check_children("MatchAs", [
            "_"
        ])

    @testutils.only_for_versions_higher("3.10")
    def test_match_node_with_match_as_capture_pattern(self):
        source = dedent("""\
            match x:
                case myval:
                    print(myval)
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        self.assert_single_case_match_block(checker, "MatchAs")
        checker.check_children("MatchAs", [
            "myval"
        ])

    @testutils.only_for_versions_higher("3.10")
    def test_match_node_with_match_as_capture_pattern_with_explicit_name(self):
        source = dedent("""\
            match x:
                case "foo" as myval:
                    print(myval)
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        self.assert_single_case_match_block(checker, "MatchAs")
        checker.check_children("MatchAs", [
            "MatchValue",
            " ",
            "as",
            " ",
            "myval",
        ])

    @testutils.only_for_versions_higher("3.10")
    def test_match_node_with_match_class_simple_match_as_capture_pattern(self):
        source = dedent("""\
            match x:
                case Foo(x):
                    print(x)
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        self.assert_single_case_match_block(checker, "MatchClass")
        checker.check_children("MatchClass", [
            "Name",
            "",
            "(",
            "",
            "MatchAs",
            "",
            ")",
        ])

    @testutils.only_for_versions_higher("3.10")
    def test_match_node_with_match_class_named_argument(self):
        source = dedent("""\
            match x:
                case Foo(x=10, y="20"):
                    print(x)
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        self.assert_single_case_match_block(checker, "MatchClass")
        checker.check_children("MatchClass", [
            "Name",
            "",
            "(",
            "",
            "x",
            "",
            "=",
            "",
            "MatchValue",
            "",
            ",",
            " ",
            "y",
            "",
            "=",
            "",
            "MatchValue",
            "",
            ")",
        ])

    @testutils.only_for_versions_higher("3.10")
    def test_match_node_with_match_class_match_as_capture_pattern_with_explicit_name(self):
        source = dedent("""\
            match x:
                case Foo(x) as b:
                    print(x)
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        self.assert_single_case_match_block(checker, "MatchAs")
        checker.check_children("MatchAs", [
            "MatchClass",
            " ",
            "as",
            " ",
            "b",
        ])
        checker.check_children("MatchClass", [
            "Name",
            "",
            "(",
            "",
            "MatchAs",
            "",
            ")",
        ])

    @testutils.only_for_versions_higher("3.10")
    def test_match_node_with_match_mapping_match_as(self):
        source = dedent("""\
            match x:
                case {"a": b} as c:
                    print(x)
        """)
        ast_frag = patchedast.get_patched_ast(source, True)
        checker = _ResultChecker(self, ast_frag)
        self.assert_single_case_match_block(checker, "MatchAs")
        checker.check_children("MatchAs", [
            "MatchMapping",
            " ",
            "as",
            " ",
            "c",
        ])
        checker.check_children("MatchMapping", [
            "{",
            "",
            "Str",
            "",
            ":",
            " ",
            "MatchAs",
            "",
            "}",
        ])


class _ResultChecker:
    def __init__(self, test_case, ast):
        self.test_case = test_case
        self.ast = ast

    def check_region(self, text, start, end):
        node = self._find_node(text)
        if node is None:
            self.test_case.fail("Node <%s> cannot be found" % text)
        self.test_case.assertEqual((start, end), node.region)

    def _find_node(self, text):
        """
        Find the node in `self.ast` whose type is named in `text`.

        :param text: ast node name

        Generally, the test should only have a single matching node, as it make
        the test much harder to understand when there may be multiple matches.

        If `self.ast` contains more than one nodes that matches `text`, then
        the **outer-most last match** takes precedence.

        For example, given that we are looking for `ast.Call` node:

            checker._find_node("Call")

        and given that `self.ast` is the AST for this code:

            func_a(1, func_b(2, 3)) + func_c(4, func_d(5, 6))

        the outer-most last match would be the ast node representing this bit:

            func_c(4, func_d(5, 6))

        Note that the order of traversal is based on the order of ast nodes,
        which usually, but not always, match textual order.
        """
        goal = text
        if not isinstance(text, (tuple, list)):
            goal = [text]

        class Search:
            result = None

            def __call__(self, node):
                for text in goal:
                    if str(node).startswith(text):
                        self.result = node
                        break
                    if ast.get_node_type_name(node).startswith(text):
                        self.result = node
                        break
                return self.result is not None

        search = Search()
        ast.call_for_nodes(self.ast, search)
        return search.result

    def check_children(self, text, children):
        node = self._find_node(text)
        if node is None:
            self.test_case.fail("Node <%s> cannot be found" % text)
        result = list(node.sorted_children)
        self.test_case.assertEqual(len(children), len(result))
        for expected, child in zip(children, result):
            goals = expected
            if not isinstance(expected, (tuple, list)):
                goals = [expected]
            for goal in goals:
                if goal == "" or isinstance(child, (str, bytes)):
                    self.test_case.assertEqual(goal, child)
                    break
            else:
                self.test_case.assertNotEqual("", text, "probably ignoring some node")
                self.test_case.assertTrue(
                    ast.get_node_type_name(child).startswith(expected),
                    msg="Expected <%s> but was <%s>"
                    % (expected, ast.get_node_type_name(child)),
                )
