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
        testmod = testutils.create_module(self.project, 'testmod')
        testmod.write(source_code)
        extractor = extract.ExtractMethod(
            self.project, testmod, start, end)
        self.project.do(extractor.get_changes(extracted, **kwds))
        return testmod.read()

    def do_extract_variable(self, source_code, start, end, extracted, **kwds):
        testmod = testutils.create_module(self.project, 'testmod')
        testmod.write(source_code)
        extractor = extract.ExtractVariable(self.project, testmod, start, end)
        self.project.do(extractor.get_changes(extracted, **kwds))
        return testmod.read()

    def _convert_line_range_to_offset(self, code, start, end):
        lines = rope.base.codeanalyze.SourceLinesAdapter(code)
        return lines.get_line_start(start), lines.get_line_end(end)

    def test_simple_extract_function(self):
        code = "def a_func():\n    print('one')\n    print('two')\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'extracted')
        expected = "def a_func():\n    extracted()\n    print('two')\n\n" \
                   "def extracted():\n    print('one')\n"
        self.assertEqual(expected, refactored)

    def test_extract_function_at_the_end_of_file(self):
        code = "def a_func():\n    print('one')"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'extracted')
        expected = "def a_func():\n    extracted()\n" \
                   "def extracted():\n    print('one')\n"
        self.assertEqual(expected, refactored)

    def test_extract_function_after_scope(self):
        code = "def a_func():\n    print('one')\n    print('two')" \
            "\n\nprint('hey')\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'extracted')
        expected = "def a_func():\n    extracted()\n    print('two')\n\n" \
                   "def extracted():\n    print('one')\n\nprint('hey')\n"
        self.assertEqual(expected, refactored)

    @testutils.only_for('3.5')
    def test_extract_function_containing_dict_generalized_unpacking(self):
        code = dedent('''\
            def a_func(dict1):
                dict2 = {}
                a_var = {a: b, **dict1, **dict2}
        ''')
        start = code.index('{a')
        end = code.index('2}') + len('2}')
        refactored = self.do_extract_method(code, start, end, 'extracted')
        expected = dedent('''\
            def a_func(dict1):
                dict2 = {}
                a_var = extracted(dict1, dict2)

            def extracted(dict1, dict2):
                return {a: b, **dict1, **dict2}
        ''')
        self.assertEqual(expected, refactored)

    def test_simple_extract_function_with_parameter(self):
        code = "def a_func():\n    a_var = 10\n    print(a_var)\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    new_func(a_var)\n\n" \
                   "def new_func(a_var):\n    print(a_var)\n"
        self.assertEqual(expected, refactored)

    def test_not_unread_variables_as_parameter(self):
        code = "def a_func():\n    a_var = 10\n    print('hey')\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    new_func()\n\n" \
                   "def new_func():\n    print('hey')\n"
        self.assertEqual(expected, refactored)

    def test_simple_extract_function_with_two_parameter(self):
        code = 'def a_func():\n    a_var = 10\n    another_var = 20\n' \
               '    third_var = a_var + another_var\n'
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n    a_var = 10\n    another_var = 20\n' \
                   '    new_func(a_var, another_var)\n\n' \
                   'def new_func(a_var, another_var):\n' \
                   '    third_var = a_var + another_var\n'
        self.assertEqual(expected, refactored)

    def test_simple_extract_function_with_return_value(self):
        code = 'def a_func():\n    a_var = 10\n    print(a_var)\n'
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n    a_var = new_func()' \
                   '\n    print(a_var)\n\n' \
                   'def new_func():\n    a_var = 10\n    return a_var\n'
        self.assertEqual(expected, refactored)

    def test_extract_function_with_multiple_return_values(self):
        code = 'def a_func():\n    a_var = 10\n    another_var = 20\n' \
               '    third_var = a_var + another_var\n'
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n    a_var, another_var = new_func()\n' \
                   '    third_var = a_var + another_var\n\n' \
                   'def new_func():\n    a_var = 10\n    another_var = 20\n' \
                   '    return a_var, another_var\n'
        self.assertEqual(expected, refactored)

    def test_simple_extract_method(self):
        code = 'class AClass(object):\n\n' \
               '    def a_func(self):\n        print(1)\n        print(2)\n'
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'class AClass(object):\n\n' \
                   '    def a_func(self):\n' \
                   '        self.new_func()\n' \
                   '        print(2)\n\n' \
                   '    def new_func(self):\n        print(1)\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_with_args_and_returns(self):
        code = 'class AClass(object):\n' \
               '    def a_func(self):\n' \
               '        a_var = 10\n' \
               '        another_var = a_var * 3\n' \
               '        third_var = a_var + another_var\n'
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'class AClass(object):\n' \
                   '    def a_func(self):\n' \
                   '        a_var = 10\n' \
                   '        another_var = self.new_func(a_var)\n' \
                   '        third_var = a_var + another_var\n\n' \
                   '    def new_func(self, a_var):\n' \
                   '        another_var = a_var * 3\n' \
                   '        return another_var\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_with_self_as_argument(self):
        code = 'class AClass(object):\n' \
               '    def a_func(self):\n' \
               '        print(self)\n'
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'class AClass(object):\n' \
                   '    def a_func(self):\n' \
                   '        self.new_func()\n\n' \
                   '    def new_func(self):\n' \
                   '        print(self)\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_with_no_self_as_argument(self):
        code = 'class AClass(object):\n' \
               '    def a_func():\n' \
               '        print(1)\n'
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_extract_method_with_multiple_methods(self):
        code = 'class AClass(object):\n' \
               '    def a_func(self):\n' \
               '        print(self)\n\n' \
               '    def another_func(self):\n' \
               '        pass\n'
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'class AClass(object):\n' \
                   '    def a_func(self):\n' \
                   '        self.new_func()\n\n' \
                   '    def new_func(self):\n' \
                   '        print(self)\n\n' \
                   '    def another_func(self):\n' \
                   '        pass\n'
        self.assertEqual(expected, refactored)

    def test_extract_function_with_function_returns(self):
        code = 'def a_func():\n    def inner_func():\n        pass\n' \
               '    inner_func()\n'
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n' \
                   '    inner_func = new_func()\n    inner_func()\n\n' \
                   'def new_func():\n' \
                   '    def inner_func():\n        pass\n' \
                   '    return inner_func\n'
        self.assertEqual(expected, refactored)

    def test_simple_extract_global_function(self):
        code = "print('one')\nprint('two')\nprint('three')\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "print('one')\n\ndef new_func():\n    print('two')\n" \
                   "\nnew_func()\nprint('three')\n"
        self.assertEqual(expected, refactored)

    def test_extract_global_function_inside_ifs(self):
        code = 'if True:\n    a = 10\n'
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = '\ndef new_func():\n    a = 10\n\nif True:\n' \
                   '    new_func()\n'
        self.assertEqual(expected, refactored)

    def test_extract_function_while_inner_function_reads(self):
        code = 'def a_func():\n    a_var = 10\n' \
               '    def inner_func():\n        print(a_var)\n' \
               '    return inner_func\n'
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n    a_var = 10\n' \
                   '    inner_func = new_func(a_var)' \
                   '\n    return inner_func\n\n' \
                   'def new_func(a_var):\n' \
                   '    def inner_func():\n        print(a_var)\n' \
                   '    return inner_func\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_bad_range(self):
        code = "def a_func():\n    pass\na_var = 10\n"
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_extract_method_bad_range2(self):
        code = "class AClass(object):\n    pass\n"
        start, end = self._convert_line_range_to_offset(code, 1, 1)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_extract_method_containing_return(self):
        code = 'def a_func(arg):\n    if arg:\n        return arg * 2' \
               '\n    return 1'
        start, end = self._convert_line_range_to_offset(code, 2, 4)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_extract_method_containing_yield(self):
        code = "def a_func(arg):\n    yield arg * 2\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_extract_method_containing_uncomplete_lines(self):
        code = 'a_var = 20\nanother_var = 30\n'
        start = code.index('20')
        end = code.index('30') + 2
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_extract_method_containing_uncomplete_lines2(self):
        code = 'a_var = 20\nanother_var = 30\n'
        start = code.index('20')
        end = code.index('another') + 5
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_extract_function_and_argument_as_paramenter(self):
        code = 'def a_func(arg):\n    print(arg)\n'
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func(arg):\n    new_func(arg)\n\n' \
                   'def new_func(arg):\n    print(arg)\n'
        self.assertEqual(expected, refactored)

    def test_extract_function_and_end_as_the_start_of_a_line(self):
        code = 'print("hey")\nif True:\n    pass\n'
        start = 0
        end = code.index('\n') + 1
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = '\ndef new_func():\n    print("hey")\n\n' \
                   'new_func()\nif True:\n    pass\n'
        self.assertEqual(expected, refactored)

    def test_extract_function_and_indented_blocks(self):
        code = 'def a_func(arg):\n    if True:\n' \
               '        if True:\n            print(arg)\n'
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func(arg):\n    ' \
                   'if True:\n        new_func(arg)\n\n' \
                   'def new_func(arg):\n    if True:\n        print(arg)\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_and_multi_line_headers(self):
        code = 'def a_func(\n           arg):\n    print(arg)\n'
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func(\n           arg):\n    new_func(arg)\n\n' \
                   'def new_func(arg):\n    print(arg)\n'
        self.assertEqual(expected, refactored)

    def test_single_line_extract_function(self):
        code = 'a_var = 10 + 20\n'
        start = code.index('10')
        end = code.index('20') + 2
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "\ndef new_func():\n    " \
                   "return 10 + 20\n\na_var = new_func()\n"
        self.assertEqual(expected, refactored)

    def test_single_line_extract_function2(self):
        code = 'def a_func():\n    a = 10\n    b = a * 20\n'
        start = code.rindex('a')
        end = code.index('20') + 2
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n    a = 10\n    b = new_func(a)\n' \
                   '\ndef new_func(a):\n    return a * 20\n'
        self.assertEqual(expected, refactored)

    def test_single_line_extract_method_and_logical_lines(self):
        code = 'a_var = 10 +\\\n    20\n'
        start = code.index('10')
        end = code.index('20') + 2
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = '\ndef new_func():\n    ' \
                   'return 10 + 20\n\na_var = new_func()\n'
        self.assertEqual(expected, refactored)

    def test_single_line_extract_method_and_logical_lines2(self):
        code = 'a_var = (10,\\\n    20)\n'
        start = code.index('10') - 1
        end = code.index('20') + 3
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = '\ndef new_func():\n' \
                   '    return (10, 20)\n\na_var = new_func()\n'
        self.assertEqual(expected, refactored)

    def test_single_line_extract_method(self):
        code = "class AClass(object):\n\n" \
               "    def a_func(self):\n        a = 10\n        b = a * a\n"
        start = code.rindex('=') + 2
        end = code.rindex('a') + 1
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'class AClass(object):\n\n' \
                   '    def a_func(self):\n' \
                   '        a = 10\n        b = self.new_func(a)\n\n' \
                   '    def new_func(self, a):\n        return a * a\n'
        self.assertEqual(expected, refactored)

    def test_single_line_extract_function_if_condition(self):
        code = 'if True:\n    pass\n'
        start = code.index('True')
        end = code.index('True') + 4
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "\ndef new_func():\n    return True\n\nif new_func():" \
                   "\n    pass\n"
        self.assertEqual(expected, refactored)

    def test_unneeded_params(self):
        code = 'class A(object):\n    ' \
               'def a_func(self):\n        a_var = 10\n        a_var += 2\n'
        start = code.rindex('2')
        end = code.rindex('2') + 1
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'class A(object):\n' \
                   '    def a_func(self):\n        a_var = 10\n' \
                   '        a_var += self.new_func()\n\n' \
                   '    def new_func(self):\n        return 2\n'
        self.assertEqual(expected, refactored)

    def test_breaks_and_continues_inside_loops(self):
        code = 'def a_func():\n    for i in range(10):\n        continue\n'
        start = code.index('for')
        end = len(code) - 1
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n    new_func()\n\n' \
                   'def new_func():\n' \
                   '    for i in range(10):\n        continue\n'
        self.assertEqual(expected, refactored)

    def test_breaks_and_continues_outside_loops(self):
        code = 'def a_func():\n' \
               '    for i in range(10):\n        a = i\n        continue\n'
        start = code.index('a = i')
        end = len(code) - 1
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_variable_writes_followed_by_variable_reads_after_extraction(self):
        code = 'def a_func():\n    a = 1\n    a = 2\n    b = a\n'
        start = code.index('a = 1')
        end = code.index('a = 2') - 1
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n    new_func()\n    a = 2\n    b = a\n\n' \
                   'def new_func():\n    a = 1\n'
        self.assertEqual(expected, refactored)

    def test_var_writes_followed_by_var_reads_inside_extraction(self):
        code = 'def a_func():\n    a = 1\n    a = 2\n    b = a\n'
        start = code.index('a = 2')
        end = len(code) - 1
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n    a = 1\n    new_func()\n\n' \
                   'def new_func():\n    a = 2\n    b = a\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable(self):
        code = 'a_var = 10 + 20\n'
        start = code.index('10')
        end = code.index('20') + 2
        refactored = self.do_extract_variable(code, start, end, 'new_var')
        expected = 'new_var = 10 + 20\na_var = new_var\n'
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher('3.6')
    def test_extract_variable_f_string(self):
        code = dedent('''\
            foo(f"abc {a_var} def", 10)
        ''')
        start = code.index('f"')
        end = code.index('def"') + 4
        refactored = self.do_extract_variable(code, start, end, 'new_var')
        expected = dedent('''\
            new_var = f"abc {a_var} def"
            foo(new_var, 10)
        ''')
        self.assertEqual(expected, refactored)

    def test_extract_variable_multiple_lines(self):
        code = 'a = 1\nb = 2\n'
        start = code.index('1')
        end = code.index('1') + 1
        refactored = self.do_extract_variable(code, start, end, 'c')
        expected = 'c = 1\na = c\nb = 2\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable_in_the_middle_of_statements(self):
        code = 'a = 1 + 2\n'
        start = code.index('1')
        end = code.index('1') + 1
        refactored = self.do_extract_variable(code, start, end, 'c')
        expected = 'c = 1\na = c + 2\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable_for_a_tuple(self):
        code = 'a = 1, 2\n'
        start = code.index('1')
        end = code.index('2') + 1
        refactored = self.do_extract_variable(code, start, end, 'c')
        expected = 'c = 1, 2\na = c\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable_for_a_string(self):
        code = 'def a_func():\n    a = "hey!"\n'
        start = code.index('"')
        end = code.rindex('"') + 1
        refactored = self.do_extract_variable(code, start, end, 'c')
        expected = 'def a_func():\n    c = "hey!"\n    a = c\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable_inside_ifs(self):
        code = 'if True:\n    a = 1 + 2\n'
        start = code.index('1')
        end = code.rindex('2') + 1
        refactored = self.do_extract_variable(code, start, end, 'b')
        expected = 'if True:\n    b = 1 + 2\n    a = b\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable_inside_ifs_and_logical_lines(self):
        code = 'if True:\n    a = (3 + \n(1 + 2))\n'
        start = code.index('1')
        end = code.index('2') + 1
        refactored = self.do_extract_variable(code, start, end, 'b')
        expected = 'if True:\n    b = 1 + 2\n    a = (3 + \n(b))\n'
        self.assertEqual(expected, refactored)

    # TODO: Handle when extracting a subexpression
    def xxx_test_extract_variable_for_a_subexpression(self):
        code = 'a = 3 + 1 + 2\n'
        start = code.index('1')
        end = code.index('2') + 1
        refactored = self.do_extract_variable(code, start, end, 'b')
        expected = 'b = 1 + 2\na = 3 + b\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable_starting_from_the_start_of_the_line(self):
        code = 'a_dict = {1: 1}\na_dict.values().count(1)\n'
        start = code.rindex('a_dict')
        end = code.index('count') - 1
        refactored = self.do_extract_variable(code, start, end, 'values')
        expected = 'a_dict = {1: 1}\n' \
            'values = a_dict.values()\nvalues.count(1)\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable_on_the_last_line_of_a_function(self):
        code = 'def f():\n    a_var = {}\n    a_var.keys()\n'
        start = code.rindex('a_var')
        end = code.index('.keys')
        refactored = self.do_extract_variable(code, start, end, 'new_var')
        expected = 'def f():\n    a_var = {}\n    ' \
            'new_var = a_var\n    new_var.keys()\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable_on_the_indented_function_statement(self):
        code = 'def f():\n    if True:\n        a_var = 1 + 2\n'
        start = code.index('1')
        end = code.index('2') + 1
        refactored = self.do_extract_variable(code, start, end, 'new_var')
        expected = 'def f():\n    if True:\n' \
                   '        new_var = 1 + 2\n        a_var = new_var\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_on_the_last_line_of_a_function(self):
        code = 'def f():\n    a_var = {}\n    a_var.keys()\n'
        start = code.rindex('a_var')
        end = code.index('.keys')
        refactored = self.do_extract_method(code, start, end, 'new_f')
        expected = 'def f():\n    a_var = {}\n    new_f(a_var).keys()\n\n' \
                   'def new_f(a_var):\n    return a_var\n'
        self.assertEqual(expected, refactored)

    def test_raising_exception_when_on_incomplete_variables(self):
        code = 'a_var = 10 + 20\n'
        start = code.index('10') + 1
        end = code.index('20') + 2
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_raising_exception_when_on_incomplete_variables_on_end(self):
        code = 'a_var = 10 + 20\n'
        start = code.index('10')
        end = code.index('20') + 1
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_raising_exception_on_bad_parens(self):
        code = 'a_var = (10 + 20) + 30\n'
        start = code.index('20')
        end = code.index('30') + 2
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_raising_exception_on_bad_operators(self):
        code = 'a_var = 10 + 20 + 30\n'
        start = code.index('10')
        end = code.rindex('+') + 1
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    # FIXME: Extract method should be more intelligent about bad ranges
    def xxx_test_raising_exception_on_function_parens(self):
        code = 'a = range(10)'
        start = code.index('(')
        end = code.rindex(')') + 1
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_extract_method_and_extra_blank_lines(self):
        code = '\nprint(1)\n'
        refactored = self.do_extract_method(code, 0, len(code), 'new_f')
        expected = '\n\ndef new_f():\n    print(1)\n\nnew_f()\n'
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher('3.6')
    def test_extract_method_f_string_extract_method(self):
        code = dedent('''\
            def func(a_var):
                foo(f"abc {a_var}", 10)
        ''')
        start = code.index('f"')
        end = code.index('}"') + 2
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = dedent('''\
            def func(a_var):
                foo(new_func(a_var), 10)

            def new_func(a_var):
                return f"abc {a_var}"
        ''')
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher('3.6')
    def test_extract_method_f_string_extract_method_complex_expression(self):
        code = dedent('''\
            def func(a_var):
                b_var = int
                c_var = 10
                fill = 10
                foo(f"abc {a_var + f'{b_var(a_var)}':{fill}16}" f"{c_var}", 10)
        ''')
        start = code.index('f"')
        end = code.index('c_var}"') + 7
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = dedent('''\
            def func(a_var):
                b_var = int
                c_var = 10
                fill = 10
                foo(new_func(a_var, b_var, c_var, fill), 10)

            def new_func(a_var, b_var, c_var, fill):
                return f"abc {a_var + f'{b_var(a_var)}':{fill}16}" f"{c_var}"
        ''')
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher('3.6')
    def test_extract_method_f_string_false_comment(self):
        code = dedent('''\
            def func(a_var):
                foo(f"abc {a_var} # ", 10)
        ''')
        start = code.index('f"')
        end = code.index('# "') + 3
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = dedent('''\
            def func(a_var):
                foo(new_func(a_var), 10)

            def new_func(a_var):
                return f"abc {a_var} # "
        ''')
        self.assertEqual(expected, refactored)

    @unittest.expectedFailure
    @testutils.only_for_versions_higher('3.6')
    def test_extract_method_f_string_false_format_value_in_regular_string(self):
        code = dedent('''\
            def func(a_var):
                b_var = 1
                foo(f"abc {a_var} " "{b_var}" f"{b_var} def", 10)
        ''')
        start = code.index('f"')
        end = code.index('def"') + 4
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = dedent('''\
            def func(a_var):
                b_var = 1
                foo(new_func(a_var, b_var), 10)

            def new_func(a_var, b_var):
                return f"abc {a_var} " "{b_var}" f"{b_var} def"
        ''')
        self.assertEqual(expected, refactored)

    def test_variable_writes_in_the_same_line_as_variable_read(self):
        code = 'a = 1\na = 1 + a\n'
        start = code.index('\n') + 1
        end = len(code)
        refactored = self.do_extract_method(code, start, end, 'new_f',
                                            global_=True)
        expected = 'a = 1\n\ndef new_f(a):\n    a = 1 + a\n\nnew_f(a)\n'
        self.assertEqual(expected, refactored)

    def test_variable_writes_in_the_same_line_as_variable_read2(self):
        code = dedent('''\
            a = 1
            a += 1
        ''')
        start = code.index('\n') + 1
        end = len(code)
        refactored = self.do_extract_method(code, start, end, 'new_f',
                                            global_=True)
        expected = dedent('''\
            a = 1

            def new_f(a):
                a += 1

            new_f(a)
        ''')
        self.assertEqual(expected, refactored)

    def test_variable_writes_in_the_same_line_as_variable_read3(self):
        code = dedent('''\
            a = 1
            a += 1
            print(a)
        ''')
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_f')
        expected = dedent('''\
            a = 1

            def new_f(a):
                a += 1
                return a

            a = new_f(a)
            print(a)
        ''')
        self.assertEqual(expected, refactored)

    def test_variable_writes_only(self):
        code = dedent('''\
            i = 1
            print(i)
        ''')
        start, end = self._convert_line_range_to_offset(code, 1, 1)
        refactored = self.do_extract_method(code, start, end, 'new_f')
        expected = dedent('''\

            def new_f():
                i = 1
                return i

            i = new_f()
            print(i)
        ''')
        self.assertEqual(expected, refactored)

    def test_variable_and_similar_expressions(self):
        code = 'a = 1\nb = 1\n'
        start = code.index('1')
        end = start + 1
        refactored = self.do_extract_variable(code, start, end,
                                              'one', similar=True)
        expected = 'one = 1\na = one\nb = one\n'
        self.assertEqual(expected, refactored)

    def test_definition_should_appear_before_the_first_use(self):
        code = 'a = 1\nb = 1\n'
        start = code.rindex('1')
        end = start + 1
        refactored = self.do_extract_variable(code, start, end,
                                              'one', similar=True)
        expected = 'one = 1\na = one\nb = one\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_and_similar_expressions(self):
        code = 'a = 1\nb = 1\n'
        start = code.index('1')
        end = start + 1
        refactored = self.do_extract_method(code, start, end,
                                            'one', similar=True)
        expected = '\ndef one():\n    return 1\n\na = one()\nb = one()\n'
        self.assertEqual(expected, refactored)

    def test_simple_extract_method_and_similar_statements(self):
        code = 'class AClass(object):\n\n' \
               '    def func1(self):\n        a = 1 + 2\n        b = a\n' \
               '    def func2(self):\n        a = 1 + 2\n        b = a\n'
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end,
                                            'new_func', similar=True)
        expected = 'class AClass(object):\n\n' \
                   '    def func1(self):\n' \
                   '        a = self.new_func()\n        b = a\n\n' \
                   '    def new_func(self):\n' \
                   '        a = 1 + 2\n        return a\n' \
                   '    def func2(self):\n' \
                   '        a = self.new_func()\n        b = a\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_and_similar_statements2(self):
        code = 'class AClass(object):\n\n' \
               '    def func1(self, p1):\n        a = p1 + 2\n' \
               '    def func2(self, p2):\n        a = p2 + 2\n'
        start = code.rindex('p1')
        end = code.index('2\n') + 1
        refactored = self.do_extract_method(code, start, end,
                                            'new_func', similar=True)
        expected = 'class AClass(object):\n\n' \
                   '    def func1(self, p1):\n        ' \
                   'a = self.new_func(p1)\n\n' \
                   '    def new_func(self, p1):\n        return p1 + 2\n' \
                   '    def func2(self, p2):\n        a = self.new_func(p2)\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_and_similar_sttemnts_return_is_different(self):
        code = 'class AClass(object):\n\n' \
               '    def func1(self, p1):\n        a = p1 + 2\n' \
               '    def func2(self, p2):\n        self.attr = p2 + 2\n'
        start = code.rindex('p1')
        end = code.index('2\n') + 1
        refactored = self.do_extract_method(code, start, end,
                                            'new_func', similar=True)
        expected = 'class AClass(object):\n\n' \
                   '    def func1(self, p1):' \
                   '\n        a = self.new_func(p1)\n\n' \
                   '    def new_func(self, p1):\n        return p1 + 2\n' \
                   '    def func2(self, p2):\n' \
                   '        self.attr = self.new_func(p2)\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_and_similar_sttemnts_overlapping_regions(self):
        code = 'def func(p):\n' \
               '    a = p\n' \
               '    b = a\n' \
               '    c = b\n' \
               '    d = c\n' \
               '    return d'
        start = code.index('a')
        end = code.rindex('a') + 1
        refactored = self.do_extract_method(
            code, start, end, 'new_func', similar=True)
        expected = 'def func(p):\n' \
                   '    b = new_func(p)\n' \
                   '    d = new_func(b)\n' \
                   '    return d\n' \
                   'def new_func(p):\n' \
                   '    a = p\n' \
                   '    b = a\n' \
                   '    return b\n'
        self.assertEqual(expected, refactored)

    def test_definition_should_appear_where_it_is_visible(self):
        code = 'if True:\n    a = 1\nelse:\n    b = 1\n'
        start = code.rindex('1')
        end = start + 1
        refactored = self.do_extract_variable(code, start, end,
                                              'one', similar=True)
        expected = 'one = 1\nif True:\n    a = one\nelse:\n    b = one\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable_and_similar_statements_in_classes(self):
        code = 'class AClass(object):\n\n' \
               '    def func1(self):\n        a = 1\n' \
               '    def func2(self):\n        b = 1\n'
        start = code.index(' 1') + 1
        refactored = self.do_extract_variable(code, start, start + 1,
                                              'one', similar=True)
        expected = 'class AClass(object):\n\n' \
                   '    def func1(self):\n        one = 1\n        a = one\n' \
                   '    def func2(self):\n        b = 1\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_in_staticmethods(self):
        code = 'class AClass(object):\n\n' \
               '    @staticmethod\n    def func2():\n        b = 1\n'
        start = code.index(' 1') + 1
        refactored = self.do_extract_method(code, start, start + 1,
                                            'one', similar=True)
        expected = 'class AClass(object):\n\n' \
                   '    @staticmethod\n    def func2():\n' \
                   '        b = AClass.one()\n\n' \
                   '    @staticmethod\n    def one():\n' \
                   '        return 1\n'
        self.assertEqual(expected, refactored)

    def test_extract_normal_method_with_staticmethods(self):
        code = 'class AClass(object):\n\n' \
               '    @staticmethod\n    def func1():\n        b = 1\n' \
               '    def func2(self):\n        b = 1\n'
        start = code.rindex(' 1') + 1
        refactored = self.do_extract_method(code, start, start + 1,
                                            'one', similar=True)
        expected = 'class AClass(object):\n\n' \
                   '    @staticmethod\n    def func1():\n        b = 1\n' \
                   '    def func2(self):\n        b = self.one()\n\n' \
                   '    def one(self):\n        return 1\n'
        self.assertEqual(expected, refactored)

    def test_extract_variable_with_no_new_lines_at_the_end(self):
        code = 'a_var = 10'
        start = code.index('10')
        end = start + 2
        refactored = self.do_extract_variable(code, start, end, 'new_var')
        expected = 'new_var = 10\na_var = new_var'
        self.assertEqual(expected, refactored)

    def test_extract_method_containing_return_in_functions(self):
        code = 'def f(arg):\n    return arg\nprint(f(1))\n'
        start, end = self._convert_line_range_to_offset(code, 1, 3)
        refactored = self.do_extract_method(code, start, end, 'a_func')
        expected = '\ndef a_func():\n    def f(arg):\n        return arg\n' \
                   '    print(f(1))\n\na_func()\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_and_varying_first_parameter(self):
        code = 'class C(object):\n' \
               '    def f1(self):\n        print(str(self))\n' \
               '    def f2(self):\n        print(str(1))\n'
        start = code.index('print(') + 6
        end = code.index('))\n') + 1
        refactored = self.do_extract_method(code, start, end,
                                            'to_str', similar=True)
        expected = 'class C(object):\n' \
                   '    def f1(self):\n        print(self.to_str())\n\n' \
                   '    def to_str(self):\n        return str(self)\n' \
                   '    def f2(self):\n        print(str(1))\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_when_an_attribute_exists_in_function_scope(self):
        code = 'class A(object):\n    def func(self):\n        pass\n' \
               'a = A()\n' \
               'def f():\n' \
               '    func = a.func()\n' \
               '    print(func)\n'

        start, end = self._convert_line_range_to_offset(code, 6, 6)
        refactored = self.do_extract_method(code, start, end, 'g')
        refactored = refactored[refactored.index('A()') + 4:]
        expected = 'def f():\n    func = g()\n    print(func)\n\n' \
                   'def g():\n    func = a.func()\n    return func\n'
        self.assertEqual(expected, refactored)

    def test_global_option_for_extract_method(self):
        code = 'def a_func():\n    print(1)\n'
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end,
                                            'extracted', global_=True)
        expected = 'def a_func():\n    extracted()\n\n' \
                   'def extracted():\n    print(1)\n'
        self.assertEqual(expected, refactored)

    def test_global_extract_method(self):
        code = 'class AClass(object):\n\n' \
               '    def a_func(self):\n        print(1)\n'
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end,
                                            'new_func', global_=True)
        expected = 'class AClass(object):\n\n' \
                   '    def a_func(self):\n        new_func()\n\n' \
                   'def new_func():\n    print(1)\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_with_multiple_methods(self):  # noqa
        code = 'class AClass(object):\n' \
               '    def a_func(self):\n' \
               '        print(1)\n\n' \
               '    def another_func(self):\n' \
               '        pass\n'
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end,
                                            'new_func', global_=True)
        expected = 'class AClass(object):\n' \
                   '    def a_func(self):\n' \
                   '        new_func()\n\n' \
                   '    def another_func(self):\n' \
                   '        pass\n\n' \
                   'def new_func():\n' \
                   '    print(1)\n'
        self.assertEqual(expected, refactored)

    def test_where_to_seach_when_extracting_global_names(self):
        code = 'def a():\n    return 1\ndef b():\n    return 1\nb = 1\n'
        start = code.index('1')
        end = start + 1
        refactored = self.do_extract_variable(code, start, end, 'one',
                                              similar=True, global_=True)
        expected = 'def a():\n    return one\none = 1\n' \
            'def b():\n    return one\nb = one\n'
        self.assertEqual(expected, refactored)

    def test_extracting_pieces_with_distinct_temp_names(self):
        code = 'a = 1\nprint(a)\nb = 1\nprint(b)\n'
        start = code.index('a')
        end = code.index('\nb')
        refactored = self.do_extract_method(code, start, end, 'f',
                                            similar=True, global_=True)
        expected = '\ndef f():\n    a = 1\n    print(a)\n\nf()\nf()\n'
        self.assertEqual(expected, refactored)

    def test_extract_methods_in_glob_funcs_should_be_glob(self):
        code = 'def f():\n    a = 1\ndef g():\n    b = 1\n'
        start = code.rindex('1')
        refactored = self.do_extract_method(code, start, start + 1, 'one',
                                            similar=True, global_=False)
        expected = 'def f():\n    a = one()\ndef g():\n    b = one()\n\n' \
                   'def one():\n    return 1\n'
        self.assertEqual(expected, refactored)

    def test_extract_methods_in_glob_funcs_should_be_glob_2(self):
        code = 'if 1:\n    var = 2\n'
        start = code.rindex('2')
        refactored = self.do_extract_method(code, start, start + 1, 'two',
                                            similar=True, global_=False)
        expected = '\ndef two():\n    return 2\n\nif 1:\n    var = two()\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_and_try_blocks(self):
        code = 'def f():\n    try:\n        pass\n' \
               '    except Exception:\n        pass\n'
        start, end = self._convert_line_range_to_offset(code, 2, 5)
        refactored = self.do_extract_method(code, start, end, 'g')
        expected = 'def f():\n    g()\n\ndef g():\n    try:\n        pass\n' \
                   '    except Exception:\n        pass\n'
        self.assertEqual(expected, refactored)

    def test_extract_and_not_passing_global_functions(self):
        code = 'def next(p):\n    return p + 1\nvar = next(1)\n'
        start = code.rindex('next')
        refactored = self.do_extract_method(code, start, len(code) - 1, 'two')
        expected = 'def next(p):\n    return p + 1\n' \
                   '\ndef two():\n    return next(1)\n\nvar = two()\n'
        self.assertEqual(expected, refactored)

    def test_extracting_with_only_one_return(self):
        code = 'def f():\n    var = 1\n    return var\n'
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, 'g')
        expected = 'def f():\n    return g()\n\n' \
                   'def g():\n    var = 1\n    return var\n'
        self.assertEqual(expected, refactored)

    def test_extracting_variable_and_implicit_continuations(self):
        code = 's = ("1"\n  "2")\n'
        start = code.index('"')
        end = code.rindex('"') + 1
        refactored = self.do_extract_variable(code, start, end, 's2')
        expected = 's2 = "1" "2"\ns = (s2)\n'
        self.assertEqual(expected, refactored)

    def test_extracting_method_and_implicit_continuations(self):
        code = 's = ("1"\n  "2")\n'
        start = code.index('"')
        end = code.rindex('"') + 1
        refactored = self.do_extract_method(code, start, end, 'f')
        expected = '\ndef f():\n    return "1" "2"\n\ns = (f())\n'
        self.assertEqual(expected, refactored)

    def test_passing_conditional_updated_vars_in_extracted(self):
        code = 'def f(a):\n' \
               '    if 0:\n' \
               '        a = 1\n' \
               '    print(a)\n'
        start, end = self._convert_line_range_to_offset(code, 2, 4)
        refactored = self.do_extract_method(code, start, end, 'g')
        expected = 'def f(a):\n' \
                   '    g(a)\n\n' \
                   'def g(a):\n' \
                   '    if 0:\n' \
                   '        a = 1\n' \
                   '    print(a)\n'
        self.assertEqual(expected, refactored)

    def test_returning_conditional_updated_vars_in_extracted(self):
        code = 'def f(a):\n' \
               '    if 0:\n' \
               '        a = 1\n' \
               '    print(a)\n'
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, 'g')
        expected = 'def f(a):\n' \
                   '    a = g(a)\n' \
                   '    print(a)\n\n' \
                   'def g(a):\n' \
                   '    if 0:\n' \
                   '        a = 1\n' \
                   '    return a\n'
        self.assertEqual(expected, refactored)

    def test_extract_method_with_variables_possibly_written_to(self):
        code = "def a_func(b):\n" \
               "    if b > 0:\n" \
               "        a = 2\n" \
               "    print(a)\n"
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, 'extracted')
        expected = "def a_func(b):\n" \
                   "    a = extracted(b)\n" \
                   "    print(a)\n\n" \
                   "def extracted(b):\n" \
                   "    if b > 0:\n" \
                   "        a = 2\n" \
                   "    return a\n"
        self.assertEqual(expected, refactored)

    def test_extract_method_with_list_comprehension(self):
        code = "def foo():\n" \
               "    x = [e for e in []]\n" \
               "    f = 23\n" \
               "\n" \
               "    for e, f in []:\n" \
               "        def bar():\n" \
               "            e[42] = 1\n"
        start, end = self._convert_line_range_to_offset(code, 4, 7)
        refactored = self.do_extract_method(code, start, end, 'baz')
        expected = "def foo():\n" \
                   "    x = [e for e in []]\n" \
                   "    f = 23\n" \
                   "\n" \
                   "    baz()\n" \
                   "\n" \
                   "def baz():\n" \
                   "    for e, f in []:\n" \
                   "        def bar():\n" \
                   "            e[42] = 1\n"
        self.assertEqual(expected, refactored)

    def test_extract_method_with_list_comprehension_and_iter(self):
        code = "def foo():\n" \
               "    x = [e for e in []]\n" \
               "    f = 23\n" \
               "\n" \
               "    for x, f in x:\n" \
               "        def bar():\n" \
               "            x[42] = 1\n"
        start, end = self._convert_line_range_to_offset(code, 4, 7)
        refactored = self.do_extract_method(code, start, end, 'baz')
        expected = "def foo():\n" \
                   "    x = [e for e in []]\n" \
                   "    f = 23\n" \
                   "\n" \
                   "    baz(x)\n" \
                   "\n" \
                   "def baz(x):\n" \
                   "    for x, f in x:\n" \
                   "        def bar():\n" \
                   "            x[42] = 1\n"
        self.assertEqual(expected, refactored)

    def test_extract_method_with_list_comprehension_and_orelse(self):
        code = "def foo():\n" \
               "    x = [e for e in []]\n" \
               "    f = 23\n" \
               "\n" \
               "    for e, f in []:\n" \
               "        def bar():\n" \
               "            e[42] = 1\n"
        start, end = self._convert_line_range_to_offset(code, 4, 7)
        refactored = self.do_extract_method(code, start, end, 'baz')
        expected = "def foo():\n" \
                   "    x = [e for e in []]\n" \
                   "    f = 23\n" \
                   "\n" \
                   "    baz()\n" \
                   "\n" \
                   "def baz():\n" \
                   "    for e, f in []:\n" \
                   "        def bar():\n" \
                   "            e[42] = 1\n"
        self.assertEqual(expected, refactored)

    def test_extract_function_with_for_else_statemant(self):
        code = 'def a_func():\n    for i in range(10):\n        a = i\n    ' \
            'else:\n        a = None\n'
        start = code.index('for')
        end = len(code) - 1
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n    new_func()\n\n' \
                   'def new_func():\n' \
                   '    for i in range(10):\n        a = i\n    else:\n' \
                   '        a = None\n'
        self.assertEqual(expected, refactored)

    def test_extract_function_with_for_else_statemant_more(self):
        """TODO: fixed code to test passed """
        code = 'def a_func():\n'\
               '    for i in range(10):\n'\
               '        a = i\n'\
               '    else:\n'\
               '        for i in range(5):\n'\
               '            b = i\n'\
               '        else:\n'\
               '            b = None\n'\
               '    a = None\n'

        start = code.index('for')
        end = len(code) - 1
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = 'def a_func():\n    new_func()\n\n' \
                   'def new_func():\n' \
                   '    for i in range(10):\n'\
                   '        a = i\n'\
                   '    else:\n'\
                   '        for i in range(5):\n'\
                   '            b = i\n'\
                   '        else:\n'\
                   '            b = None\n'\
                   '    a = None\n'
        self.assertEqual(expected, refactored)

    def test_extract_function_with_for_else_statemant_outside_loops(self):
        code = 'def a_func():\n    for i in range(10):\n        a = i\n' \
            '    else:\n        a=None\n'
        start = code.index('a = i')
        end = len(code) - 1
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            self.do_extract_method(code, start, end, 'new_func')

    def test_extract_function_with_inline_assignment_in_method(self):
        code = dedent('''\
            def foo():
                i = 1
                i += 1
                print(i)
        ''')
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = dedent('''\
            def foo():
                i = 1
                i = new_func(i)
                print(i)

            def new_func(i):
                i += 1
                return i
        ''')
        self.assertEqual(expected, refactored)

    @testutils.only_for_versions_higher('3.8')
    def test_extract_function_with_inline_assignment_in_condition(self):
        code = dedent('''\
            def foo(a):
                if i := a == 5:
                    i += 1
                print(i)
        ''')
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = dedent('''\
            def foo(a):
                i = new_func(a)
                print(i)

            def new_func(a):
                if i := a == 5:
                    i += 1
                return i
        ''')
        self.assertEqual(expected, refactored)


if __name__ == '__main__':
    unittest.main()
