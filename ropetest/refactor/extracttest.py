from textwrap import dedent

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import rope.base.codeanalyze
import rope.base.exceptions

from rope.refactor import extract
from ropetest import testutils


class ExtractMethodTest(unittest.TestCase):
    def setUp(self):
        super(ExtractMethodTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore

    def tearDown(self):
        testutils.remove_project(self.project)
        super(ExtractMethodTest, self).tearDown()

    def do_extract_method(self, source_code, start, end, extracted, **kwds):
        testmod = testutils.create_module(self.project, "testmod")
        testmod.write(source_code)
        extractor = extract.ExtractMethod(self.project, testmod, start, end)
        self.project.do(extractor.get_changes(extracted, **kwds))
        return testmod.read()

    def do_extract_variable(self, source_code, start, end, extracted, **kwds):
        testmod = testutils.create_module(self.project, "testmod")
        testmod.write(source_code)
        extractor = extract.ExtractVariable(self.project, testmod, start, end)
        self.project.do(extractor.get_changes(extracted, **kwds))
        return testmod.read()

    def _convert_line_range_to_offset(self, code, start, end):
        lines = rope.base.codeanalyze.SourceLinesAdapter(code)
        return lines.get_line_start(start), lines.get_line_end(end)

    def test_simple_extract_function(self):
        code = dedent("""\
            def a_func():
                print('one')
                print('two')
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, "extracted")
        expected = dedent("""\
            def a_func():
                extracted()
                print('two')

            def extracted():
                print('one')
        """)
        self.assertEqual(expected, refactored)

    def test_simple_extract_function_one_line(self):
        code = dedent("""\
            def a_func():
                resp = 'one'
                print(resp)
        """)
        selected = "'one'"
        start, end = code.index(selected), code.index(selected) + len(selected)
        refactored = self.do_extract_method(code, start, end, "extracted")
        expected = dedent("""\
            def a_func():
                resp = extracted()
                print(resp)

            def extracted():
                return 'one'
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_at_the_end_of_file(self):
        code = dedent("""\
            def a_func():
                print('one')""")
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, "extracted")
        expected = dedent("""\
            def a_func():
                extracted()
            def extracted():
                print('one')
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_after_scope(self):
        code = dedent("""\
            def a_func():
                print('one')
                print('two')

            print('hey')
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, "extracted")
        expected = dedent("""\
            def a_func():
                extracted()
                print('two')

            def extracted():
                print('one')

            print('hey')
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for("3.5")
    def test_extract_function_containing_dict_generalized_unpacking(self):
        code = dedent("""\
            def a_func(dict1):
                dict2 = {}
                a_var = {a: b, **dict1, **dict2}
        """)
        start = code.index("{a")
        end = code.index("2}") + len("2}")
        refactored = self.do_extract_method(code, start, end, "extracted")
        expected = dedent("""\
            def a_func(dict1):
                dict2 = {}
                a_var = extracted(dict1, dict2)

            def extracted(dict1, dict2):
                return {a: b, **dict1, **dict2}
        """)
        self.assertEqual(expected, refactored)

    def test_simple_extract_function_with_parameter(self):
        code = dedent("""\
            def a_func():
                a_var = 10
                print(a_var)
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                a_var = 10
                new_func(a_var)

            def new_func(a_var):
                print(a_var)
        """)
        self.assertEqual(expected, refactored)

    def test_not_unread_variables_as_parameter(self):
        code = dedent("""\
            def a_func():
                a_var = 10
                print('hey')
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                a_var = 10
                new_func()

            def new_func():
                print('hey')
        """)
        self.assertEqual(expected, refactored)

    def test_simple_extract_function_with_two_parameter(self):
        code = dedent("""\
            def a_func():
                a_var = 10
                another_var = 20
                third_var = a_var + another_var
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                a_var = 10
                another_var = 20
                new_func(a_var, another_var)

            def new_func(a_var, another_var):
                third_var = a_var + another_var
        """)
        self.assertEqual(expected, refactored)

    def test_simple_extract_function_with_return_value(self):
        code = dedent("""\
            def a_func():
                a_var = 10
                print(a_var)
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                a_var = new_func()
                print(a_var)

            def new_func():
                a_var = 10
                return a_var
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_with_multiple_return_values(self):
        code = dedent("""\
            def a_func():
                a_var = 10
                another_var = 20
                third_var = a_var + another_var
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                a_var, another_var = new_func()
                third_var = a_var + another_var

            def new_func():
                a_var = 10
                another_var = 20
                return a_var, another_var
        """)
        self.assertEqual(expected, refactored)

    def test_simple_extract_method(self):
        code = dedent("""\
            class AClass(object):

                def a_func(self):
                    print(1)
                    print(2)
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            class AClass(object):

                def a_func(self):
                    self.new_func()
                    print(2)

                def new_func(self):
                    print(1)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_args_and_returns(self):
        code = dedent("""\
            class AClass(object):
                def a_func(self):
                    a_var = 10
                    another_var = a_var * 3
                    third_var = a_var + another_var
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            class AClass(object):
                def a_func(self):
                    a_var = 10
                    another_var = self.new_func(a_var)
                    third_var = a_var + another_var

                def new_func(self, a_var):
                    another_var = a_var * 3
                    return another_var
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_self_as_argument(self):
        code = dedent("""\
            class AClass(object):
                def a_func(self):
                    print(self)
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            class AClass(object):
                def a_func(self):
                    self.new_func()

                def new_func(self):
                    print(self)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_no_self_as_argument(self):
        code = dedent("""\
            class AClass(object):
                def a_func():
                    print(1)
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_extract_method_with_multiple_methods(self):
        code = dedent("""\
            class AClass(object):
                def a_func(self):
                    print(self)

                def another_func(self):
                    pass
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            class AClass(object):
                def a_func(self):
                    self.new_func()

                def new_func(self):
                    print(self)

                def another_func(self):
                    pass
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_with_function_returns(self):
        code = dedent("""\
            def a_func():
                def inner_func():
                    pass
                inner_func()
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                inner_func = new_func()
                inner_func()

            def new_func():
                def inner_func():
                    pass
                return inner_func
        """)
        self.assertEqual(expected, refactored)

    def test_simple_extract_global_function(self):
        code = dedent("""\
            print('one')
            print('two')
            print('three')
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            print('one')

            def new_func():
                print('two')

            new_func()
            print('three')
        """)
        self.assertEqual(expected, refactored)

    def test_extract_global_function_inside_ifs(self):
        code = dedent("""\
            if True:
                a = 10
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\

            def new_func():
                a = 10

            if True:
                new_func()
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_while_inner_function_reads(self):
        code = dedent("""\
            def a_func():
                a_var = 10
                def inner_func():
                    print(a_var)
                return inner_func
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                a_var = 10
                inner_func = new_func(a_var)
                return inner_func

            def new_func(a_var):
                def inner_func():
                    print(a_var)
                return inner_func
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_bad_range(self):
        code = dedent("""\
            def a_func():
                pass
            a_var = 10
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_extract_method_bad_range2(self):
        code = dedent("""\
            class AClass(object):
                pass
        """)
        start, end = self._convert_line_range_to_offset(code, 1, 1)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_extract_method_containing_return(self):
        code = dedent("""\
            def a_func(arg):
                if arg:
                    return arg * 2
                return 1""")
        start, end = self._convert_line_range_to_offset(code, 2, 4)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_extract_method_containing_yield(self):
        code = dedent("""\
            def a_func(arg):
                yield arg * 2
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_extract_method_containing_uncomplete_lines(self):
        code = dedent("""\
            a_var = 20
            another_var = 30
        """)
        start = code.index("20")
        end = code.index("30") + 2
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_extract_method_containing_uncomplete_lines2(self):
        code = dedent("""\
            a_var = 20
            another_var = 30
        """)
        start = code.index("20")
        end = code.index("another") + 5
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_extract_function_and_argument_as_paramenter(self):
        code = dedent("""\
            def a_func(arg):
                print(arg)
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func(arg):
                new_func(arg)

            def new_func(arg):
                print(arg)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_and_end_as_the_start_of_a_line(self):
        code = dedent("""\
            print("hey")
            if True:
                pass
        """)
        start = 0
        end = code.index("\n") + 1
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\

            def new_func():
                print("hey")

            new_func()
            if True:
                pass
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_and_indented_blocks(self):
        code = dedent("""\
            def a_func(arg):
                if True:
                    if True:
                        print(arg)
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func(arg):
                if True:
                    new_func(arg)

            def new_func(arg):
                if True:
                    print(arg)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_and_multi_line_headers(self):
        code = dedent("""\
            def a_func(
                       arg):
                print(arg)
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func(
                       arg):
                new_func(arg)

            def new_func(arg):
                print(arg)
        """)
        self.assertEqual(expected, refactored)

    def test_single_line_extract_function(self):
        code = dedent("""\
            a_var = 10 + 20
        """)
        start = code.index("10")
        end = code.index("20") + 2
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\

            def new_func():
                return 10 + 20

            a_var = new_func()
        """)
        self.assertEqual(expected, refactored)

    def test_single_line_extract_function2(self):
        code = dedent("""\
            def a_func():
                a = 10
                b = a * 20
        """)
        start = code.rindex("a")
        end = code.index("20") + 2
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                a = 10
                b = new_func(a)

            def new_func(a):
                return a * 20
        """)
        self.assertEqual(expected, refactored)

    def test_single_line_extract_method_and_logical_lines(self):
        code = dedent("""\
            a_var = 10 +\\
                20
        """)
        start = code.index("10")
        end = code.index("20") + 2
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\

            def new_func():
                return 10 + 20

            a_var = new_func()
        """)
        self.assertEqual(expected, refactored)

    def test_single_line_extract_method_and_logical_lines2(self):
        code = dedent("""\
            a_var = (10,\\
                20)
        """)
        start = code.index("10") - 1
        end = code.index("20") + 3
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\

            def new_func():
                return (10, 20)

            a_var = new_func()
        """)
        self.assertEqual(expected, refactored)

    def test_single_line_extract_method_with_large_multiline_expression(self):
        code = dedent("""\
            a_var = func(
                {
                    "hello": 1,
                    "world": 2,
                },
                blah=foo,
            )
        """)
        start = code.index("{") - 1
        end = code.index("}") + 1
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\

            def new_func():
                return {
                    "hello": 1,
                    "world": 2,
                }

            a_var = func(
                new_func(),
                blah=foo,
            )
        """)
        self.assertEqual(expected, refactored)

    def test_single_line_extract_method(self):
        code = dedent("""\
            class AClass(object):

                def a_func(self):
                    a = 10
                    b = a * a
        """)
        start = code.rindex("=") + 2
        end = code.rindex("a") + 1
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            class AClass(object):

                def a_func(self):
                    a = 10
                    b = self.new_func(a)

                def new_func(self, a):
                    return a * a
        """)
        self.assertEqual(expected, refactored)

    def test_single_line_extract_function_if_condition(self):
        code = dedent("""\
            if True:
                pass
        """)
        start = code.index("True")
        end = code.index("True") + 4
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\

            def new_func():
                return True

            if new_func():
                pass
        """)
        self.assertEqual(expected, refactored)

    def test_unneeded_params(self):
        code = dedent("""\
            class A(object):
                def a_func(self):
                    a_var = 10
                    a_var += 2
        """)
        start = code.rindex("2")
        end = code.rindex("2") + 1
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            class A(object):
                def a_func(self):
                    a_var = 10
                    a_var += self.new_func()

                def new_func(self):
                    return 2
        """)
        self.assertEqual(expected, refactored)

    def test_breaks_and_continues_inside_loops(self):
        code = dedent("""\
            def a_func():
                for i in range(10):
                    continue
        """)
        start = code.index("for")
        end = len(code) - 1
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                new_func()

            def new_func():
                for i in range(10):
                    continue
        """)
        self.assertEqual(expected, refactored)

    def test_breaks_and_continues_outside_loops(self):
        code = dedent("""\
            def a_func():
                for i in range(10):
                    a = i
                    continue
        """)
        start = code.index("a = i")
        end = len(code) - 1
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_for_loop_variable_scope(self):
        code = dedent("""\
            def my_func():
                i = 0
                for dummy in range(10):
                    i += 1
                    print(i)
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 5)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def my_func():
                i = 0
                for dummy in range(10):
                    i = new_func(i)

            def new_func(i):
                i += 1
                print(i)
                return i
        """)
        self.assertEqual(expected, refactored)

    def test_for_loop_variable_scope_read_then_write(self):
        code = dedent("""\
            def my_func():
                i = 0
                for dummy in range(10):
                    a = i + 1
                    i = a + 1
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 5)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def my_func():
                i = 0
                for dummy in range(10):
                    i = new_func(i)

            def new_func(i):
                a = i + 1
                i = a + 1
                return i
        """)
        self.assertEqual(expected, refactored)

    def test_for_loop_variable_scope_write_then_read(self):
        code = dedent("""\
            def my_func():
                i = 0
                for dummy in range(10):
                    i = 'hello'
                    print(i)
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 5)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def my_func():
                i = 0
                for dummy in range(10):
                    new_func()

            def new_func():
                i = 'hello'
                print(i)
        """)
        self.assertEqual(expected, refactored)

    def test_for_loop_variable_scope_write_only(self):
        code = dedent("""\
            def my_func():
                i = 0
                for num in range(10):
                    i = 'hello' + num
                    print(i)
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def my_func():
                i = 0
                for num in range(10):
                    i = new_func(num)
                    print(i)

            def new_func(num):
                i = 'hello' + num
                return i
        """)
        self.assertEqual(expected, refactored)

    def test_variable_writes_followed_by_variable_reads_after_extraction(self):
        code = dedent("""\
            def a_func():
                a = 1
                a = 2
                b = a
        """)
        start = code.index("a = 1")
        end = code.index("a = 2") - 1
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                new_func()
                a = 2
                b = a

            def new_func():
                a = 1
        """)
        self.assertEqual(expected, refactored)

    def test_var_writes_followed_by_var_reads_inside_extraction(self):
        code = dedent("""\
            def a_func():
                a = 1
                a = 2
                b = a
        """)
        start = code.index("a = 2")
        end = len(code) - 1
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                a = 1
                new_func()

            def new_func():
                a = 2
                b = a
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable(self):
        code = dedent("""\
            a_var = 10 + 20
        """)
        start = code.index("10")
        end = code.index("20") + 2
        refactored = self.do_extract_variable(code, start, end, "new_var")
        expected = dedent("""\
            new_var = 10 + 20
            a_var = new_var
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.6")
    def test_extract_variable_f_string(self):
        code = dedent("""\
            foo(f"abc {a_var} def", 10)
        """)
        start = code.index('f"')
        end = code.index('def"') + 4
        refactored = self.do_extract_variable(code, start, end, "new_var")
        expected = dedent("""\
            new_var = f"abc {a_var} def"
            foo(new_var, 10)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_multiple_lines(self):
        code = dedent("""\
            a = 1
            b = 2
        """)
        start = code.index("1")
        end = code.index("1") + 1
        refactored = self.do_extract_variable(code, start, end, "c")
        expected = dedent("""\
            c = 1
            a = c
            b = 2
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_in_the_middle_of_statements(self):
        code = dedent("""\
            a = 1 + 2
        """)
        start = code.index("1")
        end = code.index("1") + 1
        refactored = self.do_extract_variable(code, start, end, "c")
        expected = dedent("""\
            c = 1
            a = c + 2
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_for_a_tuple(self):
        code = dedent("""\
            a = 1, 2
        """)
        start = code.index("1")
        end = code.index("2") + 1
        refactored = self.do_extract_variable(code, start, end, "c")
        expected = dedent("""\
            c = 1, 2
            a = c
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_for_a_string(self):
        code = dedent("""\
            def a_func():
                a = "hey!"
        """)
        start = code.index('"')
        end = code.rindex('"') + 1
        refactored = self.do_extract_variable(code, start, end, "c")
        expected = dedent("""\
            def a_func():
                c = "hey!"
                a = c
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_inside_ifs(self):
        code = dedent("""\
            if True:
                a = 1 + 2
        """)
        start = code.index("1")
        end = code.rindex("2") + 1
        refactored = self.do_extract_variable(code, start, end, "b")
        expected = dedent("""\
            if True:
                b = 1 + 2
                a = b
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_inside_ifs_and_logical_lines(self):
        code = dedent("""\
            if True:
                a = (3 +
            (1 + 2))
        """)
        start = code.index("1")
        end = code.index("2") + 1
        refactored = self.do_extract_variable(code, start, end, "b")
        expected = dedent("""\
            if True:
                b = 1 + 2
                a = (3 +
            (b))
        """)
        self.assertEqual(expected, refactored)

    # TODO: Handle when extracting a subexpression
    def xxx_test_extract_variable_for_a_subexpression(self):
        code = dedent("""\
            a = 3 + 1 + 2
        """)
        start = code.index("1")
        end = code.index("2") + 1
        refactored = self.do_extract_variable(code, start, end, "b")
        expected = dedent("""\
            b = 1 + 2
            a = 3 + b
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_starting_from_the_start_of_the_line(self):
        code = dedent("""\
            a_dict = {1: 1}
            a_dict.values().count(1)
        """)
        start = code.rindex("a_dict")
        end = code.index("count") - 1
        refactored = self.do_extract_variable(code, start, end, "values")
        expected = dedent("""\
            a_dict = {1: 1}
            values = a_dict.values()
            values.count(1)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_on_the_last_line_of_a_function(self):
        code = dedent("""\
            def f():
                a_var = {}
                a_var.keys()
        """)
        start = code.rindex("a_var")
        end = code.index(".keys")
        refactored = self.do_extract_variable(code, start, end, "new_var")
        expected = dedent("""\
            def f():
                a_var = {}
                new_var = a_var
                new_var.keys()
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_on_the_indented_function_statement(self):
        code = dedent("""\
            def f():
                if True:
                    a_var = 1 + 2
        """)
        start = code.index("1")
        end = code.index("2") + 1
        refactored = self.do_extract_variable(code, start, end, "new_var")
        expected = dedent("""\
            def f():
                if True:
                    new_var = 1 + 2
                    a_var = new_var
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_on_the_last_line_of_a_function(self):
        code = dedent("""\
            def f():
                a_var = {}
                a_var.keys()
        """)
        start = code.rindex("a_var")
        end = code.index(".keys")
        refactored = self.do_extract_method(code, start, end, "new_f")
        expected = dedent("""\
            def f():
                a_var = {}
                new_f(a_var).keys()

            def new_f(a_var):
                return a_var
        """)
        self.assertEqual(expected, refactored)

    def test_raising_exception_when_on_incomplete_variables(self):
        code = dedent("""\
            a_var = 10 + 20
        """)
        start = code.index("10") + 1
        end = code.index("20") + 2
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_raising_exception_when_on_incomplete_variables_on_end(self):
        code = dedent("""\
            a_var = 10 + 20
        """)
        start = code.index("10")
        end = code.index("20") + 1
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_raising_exception_on_bad_parens(self):
        code = dedent("""\
            a_var = (10 + 20) + 30
        """)
        start = code.index("20")
        end = code.index("30") + 2
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_raising_exception_on_bad_operators(self):
        code = dedent("""\
            a_var = 10 + 20 + 30
        """)
        start = code.index("10")
        end = code.rindex("+") + 1
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    # FIXME: Extract method should be more intelligent about bad ranges
    def xxx_test_raising_exception_on_function_parens(self):
        code = dedent("""\
            a = range(10)""")
        start = code.index("(")
        end = code.rindex(")") + 1
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_extract_method_and_extra_blank_lines(self):
        code = dedent("""\

            print(1)
        """)
        refactored = self.do_extract_method(code, 0, len(code), "new_f")
        expected = dedent("""\


            def new_f():
                print(1)

            new_f()
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.6")
    def test_extract_method_f_string_extract_method(self):
        code = dedent("""\
            def func(a_var):
                foo(f"abc {a_var}", 10)
        """)
        start = code.index('f"')
        end = code.index('}"') + 2
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def func(a_var):
                foo(new_func(a_var), 10)

            def new_func(a_var):
                return f"abc {a_var}"
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.6")
    def test_extract_method_f_string_extract_method_complex_expression(self):
        code = dedent("""\
            def func(a_var):
                b_var = int
                c_var = 10
                fill = 10
                foo(f"abc {a_var + f'{b_var(a_var)}':{fill}16}" f"{c_var}", 10)
        """)
        start = code.index('f"')
        end = code.index('c_var}"') + 7
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def func(a_var):
                b_var = int
                c_var = 10
                fill = 10
                foo(new_func(a_var, b_var, c_var, fill), 10)

            def new_func(a_var, b_var, c_var, fill):
                return f"abc {a_var + f'{b_var(a_var)}':{fill}16}" f"{c_var}"
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.6")
    def test_extract_method_f_string_false_comment(self):
        code = dedent("""\
            def func(a_var):
                foo(f"abc {a_var} # ", 10)
        """)
        start = code.index('f"')
        end = code.index('# "') + 3
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def func(a_var):
                foo(new_func(a_var), 10)

            def new_func(a_var):
                return f"abc {a_var} # "
        """)
        self.assertEqual(expected, refactored)

    @unittest.expectedFailure
    @testutils.only_for_versions_higher("3.6")
    def test_extract_method_f_string_false_format_value_in_regular_string(self):
        code = dedent("""\
            def func(a_var):
                b_var = 1
                foo(f"abc {a_var} " "{b_var}" f"{b_var} def", 10)
        """)
        start = code.index('f"')
        end = code.index('def"') + 4
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def func(a_var):
                b_var = 1
                foo(new_func(a_var, b_var), 10)

            def new_func(a_var, b_var):
                return f"abc {a_var} " "{b_var}" f"{b_var} def"
        """)
        self.assertEqual(expected, refactored)

    def test_variable_writes_in_the_same_line_as_variable_read(self):
        code = dedent("""\
            a = 1
            a = 1 + a
        """)
        start = code.index("\n") + 1
        end = len(code)
        refactored = self.do_extract_method(code, start, end, "new_f", global_=True)
        expected = dedent("""\
            a = 1

            def new_f(a):
                a = 1 + a

            new_f(a)
        """)
        self.assertEqual(expected, refactored)

    def test_variable_writes_in_the_same_line_as_variable_read2(self):
        code = dedent("""\
            a = 1
            a += 1
        """)
        start = code.index("\n") + 1
        end = len(code)
        refactored = self.do_extract_method(code, start, end, "new_f", global_=True)
        expected = dedent("""\
            a = 1

            def new_f(a):
                a += 1

            new_f(a)
        """)
        self.assertEqual(expected, refactored)

    def test_variable_writes_in_the_same_line_as_variable_read3(self):
        code = dedent("""\
            a = 1
            a += 1
            print(a)
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, "new_f")
        expected = dedent("""\
            a = 1

            def new_f(a):
                a += 1
                return a

            a = new_f(a)
            print(a)
        """)
        self.assertEqual(expected, refactored)

    def test_variable_writes_only(self):
        code = dedent("""\
            i = 1
            print(i)
        """)
        start, end = self._convert_line_range_to_offset(code, 1, 1)
        refactored = self.do_extract_method(code, start, end, "new_f")
        expected = dedent("""\

            def new_f():
                i = 1
                return i

            i = new_f()
            print(i)
        """)
        self.assertEqual(expected, refactored)

    def test_variable_and_similar_expressions(self):
        code = dedent("""\
            a = 1
            b = 1
        """)
        start = code.index("1")
        end = start + 1
        refactored = self.do_extract_variable(code, start, end, "one", similar=True)
        expected = dedent("""\
            one = 1
            a = one
            b = one
        """)
        self.assertEqual(expected, refactored)

    def test_definition_should_appear_before_the_first_use(self):
        code = dedent("""\
            a = 1
            b = 1
        """)
        start = code.rindex("1")
        end = start + 1
        refactored = self.do_extract_variable(code, start, end, "one", similar=True)
        expected = dedent("""\
            one = 1
            a = one
            b = one
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_and_similar_expressions(self):
        code = dedent("""\
            a = 1
            b = 1
        """)
        start = code.index("1")
        end = start + 1
        refactored = self.do_extract_method(code, start, end, "one", similar=True)
        expected = dedent("""\

            def one():
                return 1

            a = one()
            b = one()
        """)
        self.assertEqual(expected, refactored)

    def test_simple_extract_method_and_similar_statements(self):
        code = dedent("""\
            class AClass(object):

                def func1(self):
                    a = 1 + 2
                    b = a
                def func2(self):
                    a = 1 + 2
                    b = a
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, "new_func", similar=True)
        expected = dedent("""\
            class AClass(object):

                def func1(self):
                    a = self.new_func()
                    b = a

                def new_func(self):
                    a = 1 + 2
                    return a
                def func2(self):
                    a = self.new_func()
                    b = a
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_and_similar_statements2(self):
        code = dedent("""\
            class AClass(object):

                def func1(self, p1):
                    a = p1 + 2
                def func2(self, p2):
                    a = p2 + 2
        """)
        start = code.rindex("p1")
        end = code.index("2\n") + 1
        refactored = self.do_extract_method(code, start, end, "new_func", similar=True)
        expected = dedent("""\
            class AClass(object):

                def func1(self, p1):
                    a = self.new_func(p1)

                def new_func(self, p1):
                    return p1 + 2
                def func2(self, p2):
                    a = self.new_func(p2)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_and_similar_sttemnts_return_is_different(self):
        code = dedent("""\
            class AClass(object):

                def func1(self, p1):
                    a = p1 + 2
                def func2(self, p2):
                    self.attr = p2 + 2
        """)
        start = code.rindex("p1")
        end = code.index("2\n") + 1
        refactored = self.do_extract_method(code, start, end, "new_func", similar=True)
        expected = dedent("""\
            class AClass(object):

                def func1(self, p1):
                    a = self.new_func(p1)

                def new_func(self, p1):
                    return p1 + 2
                def func2(self, p2):
                    self.attr = self.new_func(p2)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_and_similar_sttemnts_overlapping_regions(self):
        code = dedent("""\
            def func(p):
                a = p
                b = a
                c = b
                d = c
                return d""")
        start = code.index("a")
        end = code.rindex("a") + 1
        refactored = self.do_extract_method(code, start, end, "new_func", similar=True)
        expected = dedent("""\
            def func(p):
                b = new_func(p)
                d = new_func(b)
                return d
            def new_func(p):
                a = p
                b = a
                return b
        """)
        self.assertEqual(expected, refactored)

    def test_definition_should_appear_where_it_is_visible(self):
        code = dedent("""\
            if True:
                a = 1
            else:
                b = 1
        """)
        start = code.rindex("1")
        end = start + 1
        refactored = self.do_extract_variable(code, start, end, "one", similar=True)
        expected = dedent("""\
            one = 1
            if True:
                a = one
            else:
                b = one
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_and_similar_statements_in_classes(self):
        code = dedent("""\
            class AClass(object):

                def func1(self):
                    a = 1
                def func2(self):
                    b = 1
        """)
        start = code.index(" 1") + 1
        refactored = self.do_extract_variable(
            code, start, start + 1, "one", similar=True
        )
        expected = dedent("""\
            class AClass(object):

                def func1(self):
                    one = 1
                    a = one
                def func2(self):
                    b = 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_in_staticmethods(self):
        code = dedent("""\
            class AClass(object):

                @staticmethod
                def func2():
                    b = 1
        """)
        start = code.index(" 1") + 1
        refactored = self.do_extract_method(code, start, start + 1, "one", similar=True)
        expected = dedent("""\
            class AClass(object):

                @staticmethod
                def func2():
                    b = AClass.one()

                @staticmethod
                def one():
                    return 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_normal_method_with_staticmethods(self):
        code = dedent("""\
            class AClass(object):

                @staticmethod
                def func1():
                    b = 1
                def func2(self):
                    b = 1
        """)
        start = code.rindex(" 1") + 1
        refactored = self.do_extract_method(code, start, start + 1, "one", similar=True)
        expected = dedent("""\
            class AClass(object):

                @staticmethod
                def func1():
                    b = 1
                def func2(self):
                    b = self.one()

                def one(self):
                    return 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_variable_with_no_new_lines_at_the_end(self):
        code = "a_var = 10"
        start = code.index("10")
        end = start + 2
        refactored = self.do_extract_variable(code, start, end, "new_var")
        expected = dedent("""\
            new_var = 10
            a_var = new_var""")
        self.assertEqual(expected, refactored)

    def test_extract_method_containing_return_in_functions(self):
        code = dedent("""\
            def f(arg):
                return arg
            print(f(1))
        """)
        start, end = self._convert_line_range_to_offset(code, 1, 3)
        refactored = self.do_extract_method(code, start, end, "a_func")
        expected = dedent("""\

            def a_func():
                def f(arg):
                    return arg
                print(f(1))

            a_func()
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_and_varying_first_parameter(self):
        code = dedent("""\
            class C(object):
                def f1(self):
                    print(str(self))
                def f2(self):
                    print(str(1))
        """)
        start = code.index("print(") + 6
        end = code.index("))\n") + 1
        refactored = self.do_extract_method(code, start, end, "to_str", similar=True)
        expected = dedent("""\
            class C(object):
                def f1(self):
                    print(self.to_str())

                def to_str(self):
                    return str(self)
                def f2(self):
                    print(str(1))
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_when_an_attribute_exists_in_function_scope(self):
        code = dedent("""\
            class A(object):
                def func(self):
                    pass
            a = A()
            def f():
                func = a.func()
                print(func)
        """)

        start, end = self._convert_line_range_to_offset(code, 6, 6)
        refactored = self.do_extract_method(code, start, end, "g")
        refactored = refactored[refactored.index("A()") + 4 :]
        expected = dedent("""\
            def f():
                func = g()
                print(func)

            def g():
                func = a.func()
                return func
        """)
        self.assertEqual(expected, refactored)

    def test_global_option_for_extract_method(self):
        code = dedent("""\
            def a_func():
                print(1)
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, "extracted", global_=True)
        expected = dedent("""\
            def a_func():
                extracted()

            def extracted():
                print(1)
        """)
        self.assertEqual(expected, refactored)

    def test_global_extract_method(self):
        code = dedent("""\
            class AClass(object):

                def a_func(self):
                    print(1)
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, "new_func", global_=True)
        expected = dedent("""\
            class AClass(object):

                def a_func(self):
                    new_func()

            def new_func():
                print(1)
        """)
        self.assertEqual(expected, refactored)

    def test_global_extract_method_with_multiple_methods(self):
        code = dedent("""\
            class AClass(object):
                def a_func(self):
                    print(1)

                def another_func(self):
                    pass
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "new_func", global_=True)
        expected = dedent("""\
            class AClass(object):
                def a_func(self):
                    new_func()

                def another_func(self):
                    pass

            def new_func():
                print(1)
        """)
        self.assertEqual(expected, refactored)

    def test_where_to_seach_when_extracting_global_names(self):
        code = dedent("""\
            def a():
                return 1
            def b():
                return 1
            b = 1
        """)
        start = code.index("1")
        end = start + 1
        refactored = self.do_extract_variable(
            code, start, end, "one", similar=True, global_=True
        )
        expected = dedent("""\
            def a():
                return one
            one = 1
            def b():
                return one
            b = one
        """)
        self.assertEqual(expected, refactored)

    def test_extracting_pieces_with_distinct_temp_names(self):
        code = dedent("""\
            a = 1
            print(a)
            b = 1
            print(b)
        """)
        start = code.index("a")
        end = code.index("\nb")
        refactored = self.do_extract_method(
            code, start, end, "f", similar=True, global_=True
        )
        expected = dedent("""\

            def f():
                a = 1
                print(a)

            f()
            f()
        """)
        self.assertEqual(expected, refactored)

    def test_extract_methods_in_glob_funcs_should_be_glob(self):
        code = dedent("""\
            def f():
                a = 1
            def g():
                b = 1
        """)
        start = code.rindex("1")
        refactored = self.do_extract_method(
            code, start, start + 1, "one", similar=True, global_=False
        )
        expected = dedent("""\
            def f():
                a = one()
            def g():
                b = one()

            def one():
                return 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_methods_in_glob_funcs_should_be_glob_2(self):
        code = dedent("""\
            if 1:
                var = 2
        """)
        start = code.rindex("2")
        refactored = self.do_extract_method(
            code, start, start + 1, "two", similar=True, global_=False
        )
        expected = dedent("""\

            def two():
                return 2

            if 1:
                var = two()
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_and_try_blocks(self):
        code = dedent("""\
            def f():
                try:
                    pass
                except Exception:
                    pass
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 5)
        refactored = self.do_extract_method(code, start, end, "g")
        expected = dedent("""\
            def f():
                g()

            def g():
                try:
                    pass
                except Exception:
                    pass
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_and_augmentedj_assignment_in_try_block(self):
        code = dedent("""\
            def f():
                any_subscriptable = [0]
                try:
                    any_subscriptable[0] += 1
                except Exception:
                    pass
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 6)
        refactored = self.do_extract_method(code, start, end, "g")
        expected = dedent("""\
            def f():
                g()

            def g():
                any_subscriptable = [0]
                try:
                    any_subscriptable[0] += 1
                except Exception:
                    pass
        """)
        self.assertEqual(expected, refactored)

    def test_extract_and_not_passing_global_functions(self):
        code = dedent("""\
            def next(p):
                return p + 1
            var = next(1)
        """)
        start = code.rindex("next")
        refactored = self.do_extract_method(code, start, len(code) - 1, "two")
        expected = dedent("""\
            def next(p):
                return p + 1

            def two():
                return next(1)

            var = two()
        """)
        self.assertEqual(expected, refactored)

    def test_extracting_with_only_one_return(self):
        code = dedent("""\
            def f():
                var = 1
                return var
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, "g")
        expected = dedent("""\
            def f():
                return g()

            def g():
                var = 1
                return var
        """)
        self.assertEqual(expected, refactored)

    def test_extracting_variable_and_implicit_continuations(self):
        code = dedent("""\
            s = ("1"
              "2")
        """)
        start = code.index('"')
        end = code.rindex('"') + 1
        refactored = self.do_extract_variable(code, start, end, "s2")
        expected = dedent("""\
            s2 = "1" "2"
            s = (s2)
        """)
        self.assertEqual(expected, refactored)

    def test_extracting_method_and_implicit_continuations(self):
        code = dedent("""\
            s = ("1"
              "2")
        """)
        start = code.index('"')
        end = code.rindex('"') + 1
        refactored = self.do_extract_method(code, start, end, "f")
        expected = dedent("""\

            def f():
                return "1" "2"

            s = (f())
        """)
        self.assertEqual(expected, refactored)

    def test_passing_conditional_updated_vars_in_extracted(self):
        code = dedent("""\
            def f(a):
                if 0:
                    a = 1
                print(a)
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 4)
        refactored = self.do_extract_method(code, start, end, "g")
        expected = dedent("""\
            def f(a):
                g(a)

            def g(a):
                if 0:
                    a = 1
                print(a)
        """)
        self.assertEqual(expected, refactored)

    def test_returning_conditional_updated_vars_in_extracted(self):
        code = dedent("""\
            def f(a):
                if 0:
                    a = 1
                print(a)
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, "g")
        expected = dedent("""\
            def f(a):
                a = g(a)
                print(a)

            def g(a):
                if 0:
                    a = 1
                return a
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_variables_possibly_written_to(self):
        code = dedent("""\
            def a_func(b):
                if b > 0:
                    a = 2
                print(a)
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, "extracted")
        expected = dedent("""\
            def a_func(b):
                a = extracted(b)
                print(a)

            def extracted(b):
                if b > 0:
                    a = 2
                return a
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_list_comprehension(self):
        code = dedent("""\
            def foo():
                x = [e for e in []]
                f = 23

                for e, f in []:
                    def bar():
                        e[42] = 1
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 7)
        refactored = self.do_extract_method(code, start, end, "baz")
        expected = dedent("""\
            def foo():
                x = [e for e in []]
                f = 23

                baz()

            def baz():
                for e, f in []:
                    def bar():
                        e[42] = 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_list_comprehension_in_class_method(self):
        code = dedent("""\
            class SomeClass:
                def method(self):
                    result = [i for i in range(1)]
                    print(1)
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, "baz", similar=True)
        expected = dedent("""\
            class SomeClass:
                def method(self):
                    result = [i for i in range(1)]
                    self.baz()

                def baz(self):
                    print(1)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_list_comprehension_and_iter(self):
        code = dedent("""\
            def foo():
                x = [e for e in []]
                f = 23

                for x, f in x:
                    def bar():
                        x[42] = 1
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 7)
        refactored = self.do_extract_method(code, start, end, "baz")
        expected = dedent("""\
            def foo():
                x = [e for e in []]
                f = 23

                baz(x)

            def baz(x):
                for x, f in x:
                    def bar():
                        x[42] = 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_list_comprehension_and_orelse(self):
        code = dedent("""\
            def foo():
                x = [e for e in []]
                f = 23

                for e, f in []:
                    def bar():
                        e[42] = 1
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 7)
        refactored = self.do_extract_method(code, start, end, "baz")
        expected = dedent("""\
            def foo():
                x = [e for e in []]
                f = 23

                baz()

            def baz():
                for e, f in []:
                    def bar():
                        e[42] = 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_list_comprehension_multiple_targets(self):
        code = dedent("""\
            def foo():
                x = [(a, b) for a, b in []]
                f = 23
                print("hello")
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, "baz")
        expected = dedent("""\
            def foo():
                x = [(a, b) for a, b in []]
                f = 23
                baz()

            def baz():
                print("hello")
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_with_for_else_statemant(self):
        code = dedent("""\
            def a_func():
                for i in range(10):
                    a = i
                else:
                    a = None
        """)
        start = code.index("for")
        end = len(code) - 1
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                new_func()

            def new_func():
                for i in range(10):
                    a = i
                else:
                    a = None
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_with_for_else_statemant_more(self):
        """TODO: fixed code to test passed"""
        code = dedent("""\
            def a_func():
                for i in range(10):
                    a = i
                else:
                    for i in range(5):
                        b = i
                    else:
                        b = None
                a = None
        """)

        start = code.index("for")
        end = len(code) - 1
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def a_func():
                new_func()

            def new_func():
                for i in range(10):
                    a = i
                else:
                    for i in range(5):
                        b = i
                    else:
                        b = None
                a = None
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_with_for_else_statemant_outside_loops(self):
        code = dedent("""\
            def a_func():
                for i in range(10):
                    a = i
                else:
                    a=None
        """)
        start = code.index("a = i")
        end = len(code) - 1
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, "new_func")

    def test_extract_function_with_inline_assignment_in_method(self):
        code = dedent("""\
            def foo():
                i = 1
                i += 1
                print(i)
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def foo():
                i = 1
                i = new_func(i)
                print(i)

            def new_func(i):
                i += 1
                return i
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.8")
    def test_extract_function_statement_with_inline_assignment_in_condition(self):
        code = dedent("""\
            def foo(a):
                if i := a == 5:
                    i += 1
                print(i)
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def foo(a):
                i = new_func(a)
                print(i)

            def new_func(a):
                if i := a == 5:
                    i += 1
                return i
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.8")
    def test_extract_function_expression_with_inline_assignment_in_condition(self):
        code = dedent("""\
            def foo(a):
                if i := a == 5:
                    i += 1
                print(i)
        """)
        extract_target = "i := a == 5"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def foo(a):
                if i := new_func(a):
                    i += 1
                print(i)

            def new_func(a):
                return (i := a == 5)
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.8")
    def test_extract_function_expression_with_inline_assignment_complex(self):
        code = dedent("""\
            def foo(a):
                if i := a == (c := 5):
                    i += 1
                    c += 1
                print(i)
        """)
        extract_target = "i := a == (c := 5)"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def foo(a):
                if i, c := new_func(a):
                    i += 1
                    c += 1
                print(i)

            def new_func(a):
                return (i := a == (c := 5))
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.8")
    def test_extract_function_expression_with_inline_assignment_in_inner_expression(
        self,
    ):
        code = dedent("""\
            def foo(a):
                if a == (c := 5):
                    c += 1
                print(i)
        """)
        extract_target = "a == (c := 5)"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        with self.assertRaisesRegexp(
            rope.base.exceptions.RefactoringError,
            "Extracted piece cannot contain named expression \\(:= operator\\).",
        ):
            self.do_extract_method(code, start, end, "new_func")

    def test_extract_exec(self):
        code = dedent("""\
            exec("def f(): pass", {})
        """)
        start, end = self._convert_line_range_to_offset(code, 1, 1)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\

            def new_func():
                exec("def f(): pass", {})

            new_func()
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_lower("3")
    def test_extract_exec_statement(self):
        code = dedent("""\
            exec "def f(): pass" in {}
        """)
        start, end = self._convert_line_range_to_offset(code, 1, 1)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\

            def new_func():
                exec "def f(): pass" in {}

            new_func()
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.5")
    def test_extract_async_function(self):
        code = dedent("""\
            async def my_func(my_list):
                for x in my_list:
                    var = x + 1
                return var
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            async def my_func(my_list):
                for x in my_list:
                    var = new_func(x)
                return var

            def new_func(x):
                var = x + 1
                return var
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.5")
    def test_extract_inner_async_function(self):
        code = dedent("""\
            def my_func(my_list):
                async def inner_func(my_list):
                    for x in my_list:
                        var = x + 1
                return inner_func
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 4)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def my_func(my_list):
                inner_func = new_func(my_list)
                return inner_func

            def new_func(my_list):
                async def inner_func(my_list):
                    for x in my_list:
                        var = x + 1
                return inner_func
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.5")
    def test_extract_around_inner_async_function(self):
        code = dedent("""\
            def my_func(lst):
                async def inner_func(obj):
                    for x in obj:
                        var = x + 1
                return map(inner_func, lst)
        """)
        start, end = self._convert_line_range_to_offset(code, 5, 5)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            def my_func(lst):
                async def inner_func(obj):
                    for x in obj:
                        var = x + 1
                return new_func(inner_func, lst)

            def new_func(inner_func, lst):
                return map(inner_func, lst)
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.5")
    def test_extract_refactor_around_async_for_loop(self):
        code = dedent("""\
            async def my_func(my_list):
                async for x in my_list:
                    var = x + 1
                return var
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            async def my_func(my_list):
                async for x in my_list:
                    var = new_func(x)
                return var

            def new_func(x):
                var = x + 1
                return var
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.5")
    @testutils.only_for_versions_lower("3.8")
    def test_extract_refactor_containing_async_for_loop_should_error_before_py38(self):
        """
        Refactoring async/await syntaxes is only supported in Python 3.8 and
        higher because support for ast.PyCF_ALLOW_TOP_LEVEL_AWAIT was only
        added to the standard library in Python 3.8.
        """
        code = dedent("""\
            async def my_func(my_list):
                async for x in my_list:
                    var = x + 1
                return var
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        with self.assertRaisesRegexp(
            rope.base.exceptions.RefactoringError,
            "Extracted piece can only have async/await statements if Rope is running on Python 3.8 or higher",
        ):
            self.do_extract_method(code, start, end, "new_func")

    @testutils.only_for_versions_higher("3.8")
    def test_extract_refactor_containing_async_for_loop_is_supported_after_py38(self):
        code = dedent("""\
            async def my_func(my_list):
                async for x in my_list:
                    var = x + 1
                return var
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            async def my_func(my_list):
                var = new_func(my_list)
                return var

            def new_func(my_list):
                async for x in my_list:
                    var = x + 1
                return var
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.5")
    def test_extract_await_expression(self):
        code = dedent("""\
            async def my_func(my_list):
                for url in my_list:
                    resp = await request(url)
                return resp
        """)
        selected = "request(url)"
        start, end = code.index(selected), code.index(selected) + len(selected)
        refactored = self.do_extract_method(code, start, end, "new_func")
        expected = dedent("""\
            async def my_func(my_list):
                for url in my_list:
                    resp = await new_func(url)
                return resp

            def new_func(url):
                return request(url)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_to_staticmethod(self):
        code = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = a_var + 1
        """)
        extract_target = "a_var + 1"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(
            code, start, end, "second_method", kind="staticmethod"
        )
        expected = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = A.second_method(a_var)

                @staticmethod
                def second_method(a_var):
                    return a_var + 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_to_staticmethod_when_self_in_body(self):
        code = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = self.a_var + 1
        """)
        extract_target = "self.a_var + 1"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(
            code, start, end, "second_method", kind="staticmethod"
        )
        expected = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = A.second_method(self)

                @staticmethod
                def second_method(self):
                    return self.a_var + 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_from_function_to_staticmethod_raises_exception(self):
        code = dedent("""\
            def first_method():
                a_var = 1
                b_var = a_var + 1
        """)
        extract_target = "a_var + 1"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        with self.assertRaisesRegexp(
            rope.base.exceptions.RefactoringError,
            "Cannot extract to staticmethod/classmethod outside class",
        ):
            self.do_extract_method(
                code, start, end, "second_method", kind="staticmethod"
            )

    def test_extract_method_in_classmethods(self):
        code = dedent("""\
            class AClass(object):
                @classmethod
                def func2(cls):
                    b = 1
        """)
        start = code.index(" 1") + 1
        refactored = self.do_extract_method(code, start, start + 1, "one", similar=True)
        expected = dedent("""\
            class AClass(object):
                @classmethod
                def func2(cls):
                    b = AClass.one()

                @classmethod
                def one(cls):
                    return 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_from_function_to_classmethod_raises_exception(self):
        code = dedent("""\
            def first_method():
                a_var = 1
                b_var = a_var + 1
        """)
        extract_target = "a_var + 1"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        with self.assertRaisesRegexp(
            rope.base.exceptions.RefactoringError,
            "Cannot extract to staticmethod/classmethod outside class",
        ):
            self.do_extract_method(
                code, start, end, "second_method", kind="classmethod"
            )

    def test_extract_to_classmethod_when_self_in_body(self):
        code = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = self.a_var + 1
        """)
        extract_target = "self.a_var + 1"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(
            code, start, end, "second_method", kind="classmethod"
        )
        expected = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = A.second_method(self)

                @classmethod
                def second_method(cls, self):
                    return self.a_var + 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_to_classmethod(self):
        code = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = a_var + 1
        """)
        extract_target = "a_var + 1"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(
            code, start, end, "second_method", kind="classmethod"
        )
        expected = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = A.second_method(a_var)

                @classmethod
                def second_method(cls, a_var):
                    return a_var + 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_to_classmethod_when_name_starts_with_at_sign(self):
        code = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = a_var + 1
        """)
        extract_target = "a_var + 1"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "@second_method")
        expected = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = A.second_method(a_var)

                @classmethod
                def second_method(cls, a_var):
                    return a_var + 1
        """)
        self.assertEqual(expected, refactored)

    def test_extract_to_staticmethod_when_name_starts_with_dollar_sign(self):
        code = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = a_var + 1
        """)
        extract_target = "a_var + 1"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "$second_method")
        expected = dedent("""\
            class A:
                def first_method(self):
                    a_var = 1
                    b_var = A.second_method(a_var)

                @staticmethod
                def second_method(a_var):
                    return a_var + 1
        """)
        self.assertEqual(expected, refactored)

    def test_raises_exception_when_sign_in_name_and_kind_mismatch(self):
        with self.assertRaisesRegexp(
            rope.base.exceptions.RefactoringError, "Kind and shortcut in name mismatch"
        ):
            self.do_extract_method("code", 0, 1, "$second_method", kind="classmethod")

    def test_extracting_from_static_with_function_arg(self):
        code = dedent("""\
                class A:
                    @staticmethod
                    def first_method(someargs):
                        b_var = someargs + 1
            """)

        extract_target = "someargs + 1"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "second_method")
        expected = dedent("""\
                class A:
                    @staticmethod
                    def first_method(someargs):
                        b_var = A.second_method(someargs)

                    @staticmethod
                    def second_method(someargs):
                        return someargs + 1
            """)

        self.assertEqual(expected, refactored)

    def test_extract_with_list_comprehension(self):
        code = dedent("""\
            def f():
                y = [1,2,3,4]
                a = sum([x for x in y])
                b = sum([x for x in y])

                print(a, b)

            f()
        """)
        extract_target = "    a = sum([x for x in y])\n"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "_a")
        expected = dedent("""\
            def f():
                y = [1,2,3,4]
                a = _a(y)
                b = sum([x for x in y])

                print(a, b)

            def _a(y):
                a = sum([x for x in y])
                return a

            f()
        """)
        self.assertEqual(expected, refactored)

    def test_extract_with_generator(self):
        code = dedent("""\
            def f():
                y = [1,2,3,4]
                a = sum(x for x in y)
                b = sum(x for x in y)

                print(a, b)

            f()
        """)
        extract_target = "    a = sum(x for x in y)\n"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "_a")
        expected = dedent("""\
            def f():
                y = [1,2,3,4]
                a = _a(y)
                b = sum(x for x in y)

                print(a, b)

            def _a(y):
                a = sum(x for x in y)
                return a

            f()
        """)
        self.assertEqual(expected, refactored)

    def test_extract_with_set_comprehension(self):
        code = dedent("""\
            def f():
                y = [1,2,3,4]
                a = sum({x for x in y})
                b = sum({x for x in y})

                print(a, b)

            f()
        """)
        extract_target = "    a = sum({x for x in y})\n"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "_a")
        expected = dedent("""\
            def f():
                y = [1,2,3,4]
                a = _a(y)
                b = sum({x for x in y})

                print(a, b)

            def _a(y):
                a = sum({x for x in y})
                return a

            f()
        """)
        self.assertEqual(expected, refactored)

    def test_extract_with_dict_comprehension(self):
        code = dedent("""\
            def f():
                y = [1,2,3,4]
                a = sum({x: x for x in y})
                b = sum({x: x for x in y})

                print(a, b)

            f()
        """)
        extract_target = "    a = sum({x: x for x in y})\n"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "_a")
        expected = dedent("""\
            def f():
                y = [1,2,3,4]
                a = _a(y)
                b = sum({x: x for x in y})

                print(a, b)

            def _a(y):
                a = sum({x: x for x in y})
                return a

            f()
        """)
        self.assertEqual(expected, refactored)

    def test_extract_function_expression_with_assignment_to_attribute(self):
        code = dedent("""\
            class A(object):
                def func(self):
                    self.var_a = 1
                    var_bb = self.var_a
        """)
        extract_target = "= self.var_a"
        start, end = (
            code.index(extract_target) + 2,
            code.index(extract_target) + 2 + len(extract_target) - 2,
        )
        refactored = self.do_extract_method(code, start, end, "new_func", similar=True)
        expected = dedent("""\
            class A(object):
                def func(self):
                    self.var_a = 1
                    var_bb = self.new_func()

                def new_func(self):
                    return self.var_a
        """)

        self.assertEqual(expected, refactored)

    def test_extract_function_expression_with_assignment_index(self):
        code = dedent("""\
            class A(object):
                def func(self, val):
                    self[val] = 1
                    var_bb = self[val]
        """)
        extract_target = "= self[val]"
        start, end = (
            code.index(extract_target) + 2,
            code.index(extract_target) + 2 + len(extract_target) - 2,
        )
        refactored = self.do_extract_method(code, start, end, "new_func", similar=True)
        expected = dedent("""\
            class A(object):
                def func(self, val):
                    self[val] = 1
                    var_bb = self.new_func(val)

                def new_func(self, val):
                    return self[val]
        """)

        self.assertEqual(expected, refactored)

    def test_extraction_method_with_global_variable(self):
        code = dedent("""\
            g = None

            def f():
                global g

                g = 2

            f()
            print(g)
        """)
        extract_target = "g = 2"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "_g")
        expected = dedent("""\
            g = None

            def f():
                global g

                _g()

            def _g():
                global g
                g = 2

            f()
            print(g)
        """)
        self.assertEqual(expected, refactored)

    def test_extraction_method_with_global_variable_and_global_declaration(self):
        code = dedent("""\
            g = None

            def f():
                global g

                g = 2

            f()
            print(g)
        """)
        start, end = 23, 42
        refactored = self.do_extract_method(code, start, end, "_g")
        expected = dedent("""\
            g = None

            def f():
                _g()

            def _g():
                global g

                g = 2

            f()
            print(g)
        """)
        self.assertEqual(expected, refactored)

    def test_extraction_one_line_with_global_variable_read_only(self):
        code = dedent("""\
            g = None

            def f():
                global g

                a = g

            f()
            print(g)
        """)
        extract_target = "= g"
        start, end = code.index(extract_target) + 2, code.index(extract_target) + 3
        refactored = self.do_extract_method(code, start, end, "_g")
        expected = dedent("""\
            g = None

            def f():
                global g

                a = _g()

            def _g():
                return g

            f()
            print(g)
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.8")
    def test_extraction_one_line_with_global_variable(self):
        code = dedent("""\
            g = None

            def f():
                global g

                while g := 4:
                    pass

            f()
            print(g)
        """)
        extract_target = "g := 4"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "_g")
        expected = dedent("""\
            g = None

            def f():
                global g

                while _g():
                    pass

            def _g():
                global g
                return (g := 4)

            f()
            print(g)
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.8")
    def test_extraction_one_line_with_global_variable_has_postread(self):
        code = dedent("""\
            g = None

            def f():
                global g

                while g := 4:
                    print(g)

            f()
            print(g)
        """)
        extract_target = "g := 4"
        start, end = code.index(extract_target), code.index(extract_target) + len(
            extract_target
        )
        refactored = self.do_extract_method(code, start, end, "_g")
        expected = dedent("""\
            g = None

            def f():
                global g

                while g := _g():
                    print(g)

            def _g():
                global g
                return (g := 4)

            f()
            print(g)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_nested_double_with_as(self):
        code = dedent("""\
            with open("test") as file1:
                with open("test") as file2:
                    print(file1, file2)
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.do_extract_method(code, start, end, "extracted", global_=True)
        expected = dedent("""\

            def extracted(file1, file2):
                print(file1, file2)

            with open("test") as file1:
                with open("test") as file2:
                    extracted(file1, file2)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_double_with_as(self):
        code = dedent("""\
            with open("test") as file1, open("test") as file2:
                print(file1, file2)
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, "extracted", global_=True)
        expected = dedent("""\

            def extracted(file1, file2):
                print(file1, file2)

            with open("test") as file1, open("test") as file2:
                extracted(file1, file2)
        """)
        self.assertEqual(expected, refactored)

    def test_extract_method_with_nested_double_with_as_and_misleading_comment(self):
        code = dedent("""\
            with open("test") as file1, open("test") as file2:
                # with in comment
                bar()
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "extracted", global_=True)
        expected = dedent("""\

            def extracted():
                bar()

            with open("test") as file1, open("test") as file2:
                # with in comment
                extracted()
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher('3.8')
    def test_extract_method_async_with_simple(self):
        code = dedent("""\
            async def afunc():
                async with open("test") as file1:
                    print(file1)
        """)
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, "extracted", global_=True)
        expected = dedent("""\
            async def afunc():
                extracted()

            def extracted():
                async with open("test") as file1:
                    print(file1)
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher('3.8')
    def test_extract_method_containing_async_with(self):
        code = dedent("""\
            async def afunc():
                async with open("test") as file1, open("test") as file2:
                    print(file1, file2)
        """)
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, "extracted", global_=True)
        expected = dedent("""\
            async def afunc():
                async with open("test") as file1, open("test") as file2:
                    extracted(file1, file2)

            def extracted(file1, file2):
                print(file1, file2)
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.10")
    def test_extract_method_containing_structural_pattern_match(self):
        code = dedent("""\
            match var:
                case Foo("xx"):
                    print(x)
                case Foo(x):
                    print(x)
        """)
        start, end = self._convert_line_range_to_offset(code, 5, 5)
        refactored = self.do_extract_method(code, start, end, "extracted")
        expected = dedent("""\

            def extracted():
                print(x)

            match var:
                case Foo("xx"):
                    print(x)
                case Foo(x):
                    extracted()
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.10")
    def test_extract_method_containing_structural_pattern_match_2(self):
        code = dedent("""\
            def foo():
                match var:
                    case Foo(x):
                        print(x)
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, "extracted")
        expected = dedent("""\
            def foo():
                match var:
                    case Foo(x):
                        extracted(x)

            def extracted(x):
                print(x)
        """)
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher("3.10")
    def test_extract_method_containing_structural_pattern_match_3(self):
        code = dedent("""\
            def foo():
                match var:
                    case {"hello": x} as y:
                        print(x)
        """)
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, "extracted")
        expected = dedent("""\
            def foo():
                match var:
                    case {"hello": x} as y:
                        extracted(x)

            def extracted(x):
                print(x)
        """)
        self.assertEqual(expected, refactored)
