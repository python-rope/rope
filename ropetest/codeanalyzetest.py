from textwrap import dedent
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import rope.base.evaluate
from rope.base import libutils
from rope.base import exceptions, worder, codeanalyze
from rope.base.codeanalyze import (SourceLinesAdapter,
                                   LogicalLineFinder, get_block_start)
from ropetest import testutils


class SourceLinesAdapterTest(unittest.TestCase):

    def setUp(self):
        super(SourceLinesAdapterTest, self).setUp()

    def tearDown(self):
        super(SourceLinesAdapterTest, self).tearDown()

    def test_source_lines_simple(self):
        to_lines = SourceLinesAdapter('line1\nline2\n')
        self.assertEqual('line1', to_lines.get_line(1))
        self.assertEqual('line2', to_lines.get_line(2))
        self.assertEqual('', to_lines.get_line(3))
        self.assertEqual(3, to_lines.length())

    def test_source_lines_get_line_number(self):
        to_lines = SourceLinesAdapter('line1\nline2\n')
        self.assertEqual(1, to_lines.get_line_number(0))
        self.assertEqual(1, to_lines.get_line_number(5))
        self.assertEqual(2, to_lines.get_line_number(7))
        self.assertEqual(3, to_lines.get_line_number(12))

    def test_source_lines_get_line_start(self):
        to_lines = SourceLinesAdapter('line1\nline2\n')
        self.assertEqual(0, to_lines.get_line_start(1))
        self.assertEqual(6, to_lines.get_line_start(2))
        self.assertEqual(12, to_lines.get_line_start(3))

    def test_source_lines_get_line_end(self):
        to_lines = SourceLinesAdapter('line1\nline2\n')
        self.assertEqual(5, to_lines.get_line_end(1))
        self.assertEqual(11, to_lines.get_line_end(2))
        self.assertEqual(12, to_lines.get_line_end(3))

    def test_source_lines_last_line_with_no_new_line(self):
        to_lines = SourceLinesAdapter('line1')
        self.assertEqual(1, to_lines.get_line_number(5))


class WordRangeFinderTest(unittest.TestCase):

    def setUp(self):
        super(WordRangeFinderTest, self).setUp()

    def tearDown(self):
        super(WordRangeFinderTest, self).tearDown()

    def _find_primary(self, code, offset):
        word_finder = worder.Worder(code)
        result = word_finder.get_primary_at(offset)
        return result

    def test_keyword_before_parens(self):
        code = 'if (a_var).an_attr:\n    pass\n'
        self.assertEqual('(a_var).an_attr',
                          self._find_primary(code, code.index(':')))

    def test_inside_parans(self):
        code = 'a_func(a_var)'
        self.assertEqual('a_var', self._find_primary(code, 10))

    def test_simple_names(self):
        code = 'a_var = 10'
        self.assertEqual('a_var', self._find_primary(code, 3))

    def test_function_calls(self):
        code = 'sample_function()'
        self.assertEqual('sample_function', self._find_primary(code, 10))

    def test_attribute_accesses(self):
        code = 'a_var.an_attr'
        self.assertEqual('a_var.an_attr', self._find_primary(code, 10))

    def test_word_finder_on_word_beginning(self):
        code = 'print(a_var)\n'
        word_finder = worder.Worder(code)
        result = word_finder.get_word_at(code.index('a_var'))
        self.assertEqual('a_var', result)

    def test_word_finder_on_primary_beginning(self):
        code = 'print(a_var)\n'
        result = self._find_primary(code, code.index('a_var'))
        self.assertEqual('a_var', result)

    def test_word_finder_on_word_ending(self):
        code = 'print(a_var)\n'
        word_finder = worder.Worder(code)
        result = word_finder.get_word_at(code.index('a_var') + 5)
        self.assertEqual('a_var', result)

    def test_word_finder_on_primary_ending(self):
        code = 'print(a_var)\n'
        result = self._find_primary(code, code.index('a_var') + 5)
        self.assertEqual('a_var', result)

    def test_word_finder_on_primaries_with_dots_inside_parens(self):
        code = '(a_var.\nattr)'
        result = self._find_primary(code, code.index('attr') + 1)
        self.assertEqual('a_var.\nattr', result)

    def test_word_finder_on_primary_like_keyword(self):
        code = 'is_keyword = False\n'
        result = self._find_primary(code, 1)
        self.assertEqual('is_keyword', result)

    def test_keyword_before_parens_no_space(self):
        code = 'if(a_var).an_attr:\n    pass\n'
        self.assertEqual('(a_var).an_attr',
                         self._find_primary(code, code.index(':')))

    def test_strings(self):
        code = '"a string".split()'
        self.assertEqual('"a string".split', self._find_primary(code, 14))

    def test_function_calls2(self):
        code = 'file("afile.txt").read()'
        self.assertEqual('file("afile.txt").read',
                         self._find_primary(code, 18))

    def test_parens(self):
        code = '("afile.txt").split()'
        self.assertEqual('("afile.txt").split', self._find_primary(code, 18))

    def test_function_with_no_param(self):
        code = 'AClass().a_func()'
        self.assertEqual('AClass().a_func', self._find_primary(code, 12))

    def test_function_with_multiple_param(self):
        code = 'AClass(a_param, another_param, "a string").a_func()'
        self.assertEqual('AClass(a_param, another_param, "a string").a_func',
                         self._find_primary(code, 44))

    def test_param_expressions(self):
        code = 'AClass(an_object.an_attr).a_func()'
        self.assertEqual('an_object.an_attr', self._find_primary(code, 20))

    def test_string_parens(self):
        code = 'a_func("(").an_attr'
        self.assertEqual('a_func("(").an_attr', self._find_primary(code, 16))

    def test_extra_spaces(self):
        code = 'a_func  (  "(" ) .   an_attr'
        self.assertEqual('a_func  (  "(" ) .   an_attr',
                         self._find_primary(code, 26))

    def test_relative_import(self):
        code = "from .module import smt"
        self.assertEqual('.module',
                         self._find_primary(code, 5))

    def test_functions_on_ending_parens(self):
        code = 'A()'
        self.assertEqual('A()', self._find_primary(code, 2))

    def test_splitted_statement(self):
        word_finder = worder.Worder('an_object.an_attr')
        self.assertEqual(('an_object', 'an_at', 10),
                         word_finder.get_splitted_primary_before(15))

    def test_empty_splitted_statement(self):
        word_finder = worder.Worder('an_attr')
        self.assertEqual(('', 'an_at', 0),
                          word_finder.get_splitted_primary_before(5))

    def test_empty_splitted_statement2(self):
        word_finder = worder.Worder('an_object.')
        self.assertEqual(('an_object', '', 10),
                          word_finder.get_splitted_primary_before(10))

    def test_empty_splitted_statement3(self):
        word_finder = worder.Worder('')
        self.assertEqual(('', '', 0),
                          word_finder.get_splitted_primary_before(0))

    def test_empty_splitted_statement4(self):
        word_finder = worder.Worder('a_var = ')
        self.assertEqual(('', '', 8),
                          word_finder.get_splitted_primary_before(8))

    def test_empty_splitted_statement5(self):
        word_finder = worder.Worder('a.')
        self.assertEqual(('a', '', 2),
                          word_finder.get_splitted_primary_before(2))

    def test_operators_inside_parens(self):
        code = '(a_var + another_var).reverse()'
        self.assertEqual('(a_var + another_var).reverse',
                          self._find_primary(code, 25))

    def test_dictionaries(self):
        code = 'print({1: "one", 2: "two"}.keys())'
        self.assertEqual('{1: "one", 2: "two"}.keys',
                          self._find_primary(code, 29))

    def test_following_parens(self):
        code = 'a_var = a_func()()'
        result = self._find_primary(code, code.index(')(') + 3)
        self.assertEqual('a_func()()', result)

    def test_comments_for_finding_statements(self):
        code = '# var2 . \n  var3'
        self.assertEqual('var3', self._find_primary(code, code.index('3')))

    def test_str_in_comments_for_finding_statements(self):
        code = '# "var2" . \n  var3'
        self.assertEqual('var3', self._find_primary(code, code.index('3')))

    def test_comments_for_finding_statements2(self):
        code = 'var1 + "# var2".\n  var3'
        self.assertEqual('var3', self._find_primary(code, 21))

    def test_comments_for_finding_statements3(self):
        code = '"" + # var2.\n  var3'
        self.assertEqual('var3', self._find_primary(code, 21))

    def test_import_statement_finding(self):
        code = 'import mod\na_var = 10\n'
        word_finder = worder.Worder(code)
        self.assertTrue(word_finder.is_import_statement(code.index('mod') + 1))
        self.assertFalse(word_finder.is_import_statement(
            code.index('a_var') + 1))

    def test_import_statement_finding2(self):
        code = 'import a.b.c.d\nresult = a.b.c.d.f()\n'
        word_finder = worder.Worder(code)
        self.assertFalse(word_finder.is_import_statement(code.rindex('d') + 1))

    def test_word_parens_range(self):
        code = 's = str()\ns.title()\n'
        word_finder = worder.Worder(code)
        result = word_finder.get_word_parens_range(code.rindex('()') - 1)
        self.assertEqual((len(code) - 3, len(code) - 1), result)

    def test_getting_primary_before_get_index(self):
        code = '\na = (b + c).d[0]()\n'
        result = self._find_primary(code, len(code) - 2)
        self.assertEqual('(b + c).d[0]()', result)

    def test_getting_primary_and_strings_at_the_end_of_line(self):
        code = 'f(\'\\\'\')\n'
        result = self._find_primary(code, len(code) - 1)  # noqa

    def test_getting_primary_and_not_crossing_newlines(self):
        code = '\na = (b + c)\n(4 + 1).x\n'
        result = self._find_primary(code, len(code) - 1)
        self.assertEqual('(4 + 1).x', result)

    # XXX: cancatenated string literals
    def xxx_test_getting_primary_cancatenating_strs(self):
        code = 's = "a"\n"b" "c"\n'
        result = self._find_primary(code, len(code) - 2)
        self.assertEqual('"b" "c"', result)

    def test_is_a_function_being_called_with_parens_on_next_line(self):
        code = 'func\n(1, 2)\n'
        word_finder = worder.Worder(code)
        self.assertFalse(word_finder.is_a_function_being_called(1))

    # XXX: handling triple quotes
    def xxx_test_triple_quotes(self):
        code = 's = """string"""\n'
        result = self._find_primary(code, len(code) - 1)
        self.assertEqual('"""string"""', result)

    def test_triple_quotes_spanning_multiple_lines(self):
        code = 's = """\\\nl1\nl2\n """\n'
        result = self._find_primary(code, len(code) - 2)
        self.assertEqual('"""\\\nl1\nl2\n """', result)

    def test_get_word_parens_range_and_string_literals(self):
        code = 'f(1, ")", 2)\n'
        word_finder = worder.Worder(code)
        result = word_finder.get_word_parens_range(0)
        self.assertEqual((1, len(code) - 1), result)

    def test_is_assigned_here_for_equality_test(self):
        code = 'a == 1\n'
        word_finder = worder.Worder(code)
        self.assertFalse(word_finder.is_assigned_here(0))

    def test_is_assigned_here_for_not_equal_test(self):
        code = 'a != 1\n'
        word_finder = worder.Worder(code)
        self.assertFalse(word_finder.is_assigned_here(0))

    # XXX: is_assigned_here should work for tuple assignments
    def xxx_test_is_assigned_here_for_tuple_assignment(self):
        code = 'a, b = (1, 2)\n'
        word_finder = worder.Worder(code)
        self.assertTrue(word_finder.is_assigned_here(0))

    def test_is_from_with_from_import_and_multiline_parens(self):
        code = 'from mod import \\\n  (f,\n  g, h)\n'
        word_finder = worder.Worder(code)
        self.assertTrue(word_finder.is_from_statement(code.rindex('g')))

    def test_is_from_with_from_import_and_line_breaks_in_the_middle(self):
        code = 'from mod import f,\\\n g\n'
        word_finder = worder.Worder(code)
        self.assertTrue(word_finder.is_from_statement(code.rindex('g')))

    def test_one_letter_function_keyword_arguments(self):
        code = 'f(p=1)\n'
        word_finder = worder.Worder(code)
        index = code.rindex('p')
        self.assertTrue(word_finder.is_function_keyword_parameter(index))

    def test_find_parens_start(self):
        code = 'f(p)\n'
        finder = worder.Worder(code)
        self.assertEqual(1, finder.find_parens_start_from_inside(2))

    def test_underlined_find_parens_start(self):
        code = 'f(p="")\n'
        finder = worder.Worder(code)
        self.assertEqual(1, finder._find_parens_start(len(code) - 2))

    def test_find_parens_start_with_multiple_entries(self):
        code = 'myfunc(p1, p2, p3\n'
        finder = worder.Worder(code)
        self.assertEqual(code.index('('),
                          finder.find_parens_start_from_inside(len(code) - 1))

    def test_find_parens_start_with_nested_parens(self):
        code = 'myfunc(p1, (p2, p3), p4\n'
        finder = worder.Worder(code)
        self.assertEqual(code.index('('),
                          finder.find_parens_start_from_inside(len(code) - 1))

    def test_find_parens_start_with_parens_in_strs(self):
        code = 'myfunc(p1, "(", p4\n'
        finder = worder.Worder(code)
        self.assertEqual(code.index('('),
                          finder.find_parens_start_from_inside(len(code) - 1))

    def test_find_parens_start_with_parens_in_strs_in_multiple_lines(self):
        code = 'myfunc  (\np1\n , \n "(" \n, \np4\n'
        finder = worder.Worder(code)
        self.assertEqual(code.index('('),
                          finder.find_parens_start_from_inside(len(code) - 1))

    def test_is_on_function_keyword(self):
        code = 'myfunc(va'
        finder = worder.Worder(code)
        self.assertTrue(finder.is_on_function_call_keyword(len(code) - 1))

    def test_get_word_range_with_fstring(self):
        code = 'auth = 8\nmy_var = f"some value {auth}"\nprint(auth)\nother_val = "some other"'
        finder = worder.Worder(code)
        self.assertEqual(finder.get_word_range(45), (45, 49))


class ScopeNameFinderTest(unittest.TestCase):

    def setUp(self):
        super(ScopeNameFinderTest, self).setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(ScopeNameFinderTest, self).tearDown()

    # FIXME: in normal scopes the interpreter raises `UnboundLocalName`
    # exception, but not in class bodies
    def xxx_test_global_name_in_class_body(self):
        code = 'a_var = 10\nclass C(object):\n    a_var = a_var\n'
        scope = libutils.get_string_scope(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(scope.pyobject)
        result = name_finder.get_pyname_at(len(code) - 3)
        self.assertEqual(scope['a_var'], result)

    def test_class_variable_attribute_in_class_body(self):
        code = 'a_var = 10\nclass C(object):\n    a_var = a_var\n'
        scope = libutils.get_string_scope(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(scope.pyobject)
        a_var_pyname = scope['C'].get_object()['a_var']
        result = name_finder.get_pyname_at(len(code) - 12)
        self.assertEqual(a_var_pyname, result)

    def test_class_variable_attribute_in_class_body2(self):
        code = 'a_var = 10\nclass C(object):\n    a_var \\\n= a_var\n'
        scope = libutils.get_string_scope(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(scope.pyobject)
        a_var_pyname = scope['C'].get_object()['a_var']
        result = name_finder.get_pyname_at(len(code) - 12)
        self.assertEqual(a_var_pyname, result)

    def test_class_method_attribute_in_class_body(self):
        code = 'class C(object):\n    def a_method(self):\n        pass\n'
        scope = libutils.get_string_scope(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(scope.pyobject)
        a_method_pyname = scope['C'].get_object()['a_method']
        result = name_finder.get_pyname_at(code.index('a_method') + 2)
        self.assertEqual(a_method_pyname, result)

    def test_inner_class_attribute_in_class_body(self):
        code = 'class C(object):\n    class CC(object):\n        pass\n'
        scope = libutils.get_string_scope(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(scope.pyobject)
        a_class_pyname = scope['C'].get_object()['CC']
        result = name_finder.get_pyname_at(code.index('CC') + 2)
        self.assertEqual(a_class_pyname, result)

    def test_class_method_in_class_body_but_not_indexed(self):
        code = 'class C(object):\n    def func(self, func):\n        pass\n'
        scope = libutils.get_string_scope(self.project, code)
        a_func_pyname = scope.get_scopes()[0].get_scopes()[0]['func']
        name_finder = rope.base.evaluate.ScopeNameFinder(scope.pyobject)
        result = name_finder.get_pyname_at(code.index(', func') + 3)
        self.assertEqual(a_func_pyname, result)

    def test_function_but_not_indexed(self):
        code = 'def a_func(a_func):\n    pass\n'
        scope = libutils.get_string_scope(self.project, code)
        a_func_pyname = scope['a_func']
        name_finder = rope.base.evaluate.ScopeNameFinder(scope.pyobject)
        result = name_finder.get_pyname_at(code.index('a_func') + 3)
        self.assertEqual(a_func_pyname, result)

    def test_modules_after_from_statements(self):
        root_folder = self.project.root
        mod = testutils.create_module(self.project, 'mod', root_folder)
        mod.write('def a_func():\n    pass\n')
        code = 'from mod import a_func\n'
        scope = libutils.get_string_scope(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(scope.pyobject)
        mod_pyobject = self.project.get_pymodule(mod)
        found_pyname = name_finder.get_pyname_at(code.index('mod') + 1)
        self.assertEqual(mod_pyobject, found_pyname.get_object())

    def test_renaming_functions_with_from_import_and_parens(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('def afunc():\n    pass\n')
        code = 'from mod1 import (\n    afunc as func)\n'
        scope = libutils.get_string_scope(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(scope.pyobject)
        mod_pyobject = self.project.get_pymodule(mod1)
        afunc = mod_pyobject['afunc']
        found_pyname = name_finder.get_pyname_at(code.index('afunc') + 1)
        self.assertEqual(afunc.get_object(), found_pyname.get_object())

    @testutils.only_for('2.5')
    def test_relative_modules_after_from_statements(self):
        pkg1 = testutils.create_package(self.project, 'pkg1')
        pkg2 = testutils.create_package(self.project, 'pkg2', pkg1)
        mod1 = testutils.create_module(self.project, 'mod1', pkg1)
        mod2 = testutils.create_module(self.project, 'mod2', pkg2)
        mod1.write('def a_func():\n    pass\n')
        code = 'from ..mod1 import a_func\n'
        mod2.write(code)
        mod2_scope = self.project.get_pymodule(mod2).get_scope()
        name_finder = rope.base.evaluate.ScopeNameFinder(mod2_scope.pyobject)
        mod1_pyobject = self.project.get_pymodule(mod1)
        found_pyname = name_finder.get_pyname_at(code.index('mod1') + 1)
        self.assertEqual(mod1_pyobject, found_pyname.get_object())

    def test_relative_modules_after_from_statements2(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        pkg1 = testutils.create_package(self.project, 'pkg1')
        pkg2 = testutils.create_package(self.project, 'pkg2', pkg1)
        mod2 = testutils.create_module(self.project, 'mod2', pkg2)  # noqa
        mod1.write('import pkg1.pkg2.mod2')

        mod1_scope = self.project.get_pymodule(mod1).get_scope()
        name_finder = rope.base.evaluate.ScopeNameFinder(mod1_scope.pyobject)
        pkg2_pyobject = self.project.get_pymodule(pkg2)
        found_pyname = name_finder.get_pyname_at(mod1.read().index('pkg2') + 1)
        self.assertEqual(pkg2_pyobject, found_pyname.get_object())

    def test_get_pyname_at_on_language_keywords(self):
        code = 'def a_func(a_func):\n    pass\n'
        pymod = libutils.get_string_module(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(pymod)
        with self.assertRaises(exceptions.RopeError):
            name_finder.get_pyname_at(code.index('pass'))

    def test_one_liners(self):
        code = 'var = 1\ndef f(): var = 2\nprint(var)\n'
        pymod = libutils.get_string_module(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(pymod)
        pyname = name_finder.get_pyname_at(code.rindex('var'))
        self.assertEqual(pymod['var'], pyname)

    def test_one_liners_with_line_breaks(self):
        code = 'var = 1\ndef f(\n): var = 2\nprint(var)\n'
        pymod = libutils.get_string_module(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(pymod)
        pyname = name_finder.get_pyname_at(code.rindex('var'))
        self.assertEqual(pymod['var'], pyname)

    def test_one_liners_with_line_breaks2(self):
        code = 'var = 1\ndef f(\np): var = 2\nprint(var)\n'
        pymod = libutils.get_string_module(self.project, code)
        name_finder = rope.base.evaluate.ScopeNameFinder(pymod)
        pyname = name_finder.get_pyname_at(code.rindex('var'))
        self.assertEqual(pymod['var'], pyname)


class LogicalLineFinderTest(unittest.TestCase):

    def setUp(self):
        super(LogicalLineFinderTest, self).setUp()

    def tearDown(self):
        super(LogicalLineFinderTest, self).tearDown()

    def _logical_finder(self, code):
        return LogicalLineFinder(SourceLinesAdapter(code))

    def test_normal_lines(self):
        code = 'a_var = 10'
        line_finder = self._logical_finder(code)
        self.assertEqual((1, 1), line_finder.logical_line_in(1))

    def test_normal_lines2(self):
        code = 'another = 10\na_var = 20\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((1, 1), line_finder.logical_line_in(1))
        self.assertEqual((2, 2), line_finder.logical_line_in(2))

    def test_implicit_continuation(self):
        code = 'a_var = 3 + \\\n    4 + \\\n    5'
        line_finder = self._logical_finder(code)
        self.assertEqual((1, 3), line_finder.logical_line_in(2))

    def test_explicit_continuation(self):
        code = 'print(2)\na_var = (3 + \n    4, \n    5)\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((2, 4), line_finder.logical_line_in(2))

    def test_explicit_continuation_comments(self):
        code = '#\na_var = 3\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((2, 2), line_finder.logical_line_in(2))

    def test_multiple_indented_ifs(self):
        code = 'if True:\n    if True:\n        ' \
            'if True:\n            pass\n    a = 10\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((5, 5), line_finder.logical_line_in(5))

    def test_list_comprehensions_and_fors(self):
        code = 'a_list = [i\n    for i in range(10)]\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((1, 2), line_finder.logical_line_in(2))

    def test_generator_expressions_and_fors(self):
        code = 'a_list = (i\n    for i in range(10))\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((1, 2), line_finder.logical_line_in(2))

    def test_fors_and_block_start(self):
        code = 'l = range(10)\nfor i in l:\n    print(i)\n'
        self.assertEqual(2, get_block_start(SourceLinesAdapter(code), 2))

    def test_problems_with_inner_indentations(self):
        code = 'if True:\n    if True:\n        if True:\n            pass\n' \
               '    a = \\\n        1\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((5, 6), line_finder.logical_line_in(6))

    def test_problems_with_inner_indentations2(self):
        code = 'if True:\n    if True:\n        pass\n' \
               'a = 1\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((4, 4), line_finder.logical_line_in(4))

    def test_logical_lines_for_else(self):
        code = 'if True:\n    pass\nelse:\n    pass\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((3, 3), line_finder.logical_line_in(3))

    def test_logical_lines_for_lines_with_wrong_continues(self):
        code = 'var = 1 + \\'
        line_finder = self._logical_finder(code)
        self.assertEqual((1, 1), line_finder.logical_line_in(1))

    def test_logical_lines_for_multiline_string_with_extra_quotes_front(self):
        code = '""""Docs."""\na = 1\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((2, 2), line_finder.logical_line_in(2))

    def test_logical_lines_for_multiline_string_with_escaped_quotes(self):
        code = '"""Quotes \\""" "\\"" \' """\na = 1\n'
        line_finder = self._logical_finder(code)
        self.assertEqual((2, 2), line_finder.logical_line_in(2))

    def test_generating_line_starts(self):
        code = 'a = 1\na = 2\n\na = 3\n'
        line_finder = self._logical_finder(code)
        self.assertEqual([1, 2, 4], list(line_finder.generate_starts()))

    def test_generating_line_starts2(self):
        code = 'a = 1\na = 2\n\na = \\ 3\n'
        line_finder = self._logical_finder(code)
        self.assertEqual([2, 4], list(line_finder.generate_starts(2)))

    def test_generating_line_starts3(self):
        code = 'a = 1\na = 2\n\na = \\ 3\n'
        line_finder = self._logical_finder(code)
        self.assertEqual([2], list(line_finder.generate_starts(2, 3)))

    def test_generating_line_starts_for_multi_line_statements(self):
        code = '\na = \\\n 1 + \\\n 1\n'
        line_finder = self._logical_finder(code)
        self.assertEqual([2], list(line_finder.generate_starts()))

    def test_generating_line_starts_and_unmatched_deindents(self):
        code = 'if True:\n    if True:\n        if True:\n' \
               '            a = 1\n    b = 1\n'
        line_finder = self._logical_finder(code)
        self.assertEqual([4, 5], list(line_finder.generate_starts(4)))

    def test_false_triple_quoted_string(self):
        code = dedent("""\
            def foo():
                a = 0
                p = 'foo'''

            def bar():
                a = 1
                a += 1
        """)
        line_finder = self._logical_finder(code)
        self.assertEqual([1, 2, 3, 5, 6, 7], list(line_finder.generate_starts()))
        self.assertEqual((3, 3), line_finder.logical_line_in(3))
        self.assertEqual([5, 6, 7], list(line_finder.generate_starts(4)))


class TokenizerLogicalLineFinderTest(LogicalLineFinderTest):

    def _logical_finder(self, code):
        lines = SourceLinesAdapter(code)
        return codeanalyze.CachingLogicalLineFinder(
            lines, codeanalyze.tokenizer_generator)


class CustomLogicalLineFinderTest(LogicalLineFinderTest):

    def _logical_finder(self, code):
        lines = SourceLinesAdapter(code)
        return codeanalyze.CachingLogicalLineFinder(
            lines, codeanalyze.custom_generator)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(SourceLinesAdapterTest))
    result.addTests(unittest.makeSuite(WordRangeFinderTest))
    result.addTests(unittest.makeSuite(ScopeNameFinderTest))
    result.addTests(unittest.makeSuite(LogicalLineFinderTest))
    result.addTests(unittest.makeSuite(TokenizerLogicalLineFinderTest))
    result.addTests(unittest.makeSuite(CustomLogicalLineFinderTest))
    return result

if __name__ == '__main__':
    unittest.main()
