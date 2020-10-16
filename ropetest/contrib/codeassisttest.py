# coding: utf-8

import os.path
from textwrap import dedent
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.base import exceptions
from rope.contrib.codeassist import (get_definition_location, get_doc,
                                     starting_expression, code_assist,
                                     sorted_proposals, starting_offset,
                                     get_calltip, get_canonical_path)
from ropetest import testutils

try:
    unicode
except NameError:
    unicode = str


class CodeAssistTest(unittest.TestCase):

    def setUp(self):
        super(CodeAssistTest, self).setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(CodeAssistTest, self).tearDown()

    def _assist(self, code, offset=None, **args):
        if offset is None:
            offset = len(code)
        return code_assist(self.project, code, offset, **args)

    def test_simple_assist(self):
        self._assist('', 0)

    def assert_completion_in_result(self, name, scope, result, type=None):
        for proposal in result:
            if proposal.name == name:
                self.assertEqual(scope, proposal.scope,
                                 "proposal <%s> has wrong scope, expected "
                                 "%r, got %r" % (name, scope, proposal.scope))
                if type is not None:
                    self.assertEqual(type, proposal.type,
                                     "proposal <%s> has wrong type, expected "
                                     "%r, got %r" %
                                     (name, type, proposal.type))
                return
        self.fail('completion <%s> not proposed' % name)

    def assert_completion_not_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                self.fail('completion <%s> was proposed' % name)

    def test_completing_global_variables(self):
        code = 'my_global = 10\nt = my'
        result = self._assist(code)
        self.assert_completion_in_result('my_global', 'global', result)

    def test_not_proposing_unmatched_vars(self):
        code = 'my_global = 10\nt = you'
        result = self._assist(code)
        self.assert_completion_not_in_result('my_global', 'global', result)

    def test_not_proposing_unmatched_vars_with_underlined_starting(self):
        code = 'my_global = 10\nt = your_'
        result = self._assist(code)
        self.assert_completion_not_in_result('my_global', 'global', result)

    def test_not_proposing_local_assigns_as_global_completions(self):
        code = 'def f():    my_global = 10\nt = my_'
        result = self._assist(code)
        self.assert_completion_not_in_result('my_global', 'global', result)

    def test_proposing_functions(self):
        code = 'def my_func():    return 2\nt = my_'
        result = self._assist(code)
        self.assert_completion_in_result('my_func', 'global', result)

    def test_proposing_classes(self):
        code = 'class Sample(object):    pass\nt = Sam'
        result = self._assist(code)
        self.assert_completion_in_result('Sample', 'global', result)

    def test_proposing_each_name_at_most_once(self):
        code = 'variable = 10\nvariable = 20\nt = vari'
        result = self._assist(code)
        count = len([x for x in result
                     if x.name == 'variable' and x.scope == 'global'])
        self.assertEqual(1, count)

    def test_throwing_exception_in_case_of_syntax_errors(self):
        code = 'sample (sdf+)\n'
        with self.assertRaises(exceptions.ModuleSyntaxError):
            self._assist(code, maxfixes=0)

    def test_fixing_errors_with_maxfixes(self):
        code = 'def f():\n    sldj sldj\ndef g():\n    ran'
        result = self._assist(code, maxfixes=2)
        self.assertTrue(len(result) > 0)

    def test_ignoring_errors_in_current_line(self):
        code = 'def my_func():\n    return 2\nt = '
        result = self._assist(code)
        self.assert_completion_in_result('my_func', 'global', result)

    def test_not_reporting_variables_in_current_line(self):
        code = 'def my_func():    return 2\nt = my_'
        result = self._assist(code)
        self.assert_completion_not_in_result('my_', 'global', result)

    def test_completion_result(self):
        code = 'my_global = 10\nt = my'
        self.assertEqual(len(code) - 2, starting_offset(code, len(code)))

    def test_completing_imported_names(self):
        code = 'import sys\na = sy'
        result = self._assist(code)
        self.assert_completion_in_result('sys', 'imported', result)

    def test_completing_imported_names_with_as(self):
        code = 'import sys as mysys\na = mys'
        result = self._assist(code)
        self.assert_completion_in_result('mysys', 'imported', result)

    def test_not_completing_imported_names_with_as(self):
        code = 'import sys as mysys\na = sy'
        result = self._assist(code)
        self.assert_completion_not_in_result('sys', 'global', result)

    def test_including_matching_builtins_types(self):
        code = 'my_var = Excep'
        result = self._assist(code)
        self.assert_completion_in_result('Exception', 'builtin', result)
        self.assert_completion_not_in_result('zip', 'builtin', result)

    def test_including_matching_builtins_functions(self):
        code = 'my_var = zi'
        result = self._assist(code)
        self.assert_completion_in_result('zip', 'builtin', result)

    def test_builtin_instances(self):
        # ``import_dynload_stdmods`` pref is disabled for test project.
        # we need to have it enabled to make pycore._find_module()
        # load ``sys`` module.
        self.project.prefs['import_dynload_stdmods'] = True
        code = 'from sys import stdout\nstdout.wr'
        result = self._assist(code)
        self.assert_completion_in_result('write', 'builtin', result)
        self.assert_completion_in_result('writelines', 'builtin', result)

    def test_including_keywords(self):
        code = 'fo'
        result = self._assist(code)
        self.assert_completion_in_result('for', 'keyword', result)

    def test_not_reporting_proposals_after_dot(self):
        code = 'a_dict = {}\nkey = 3\na_dict.ke'
        result = self._assist(code)
        self.assert_completion_not_in_result('key', 'global', result)

    def test_proposing_local_variables_in_functions(self):
        code = 'def f(self):\n    my_var = 10\n    my_'
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'local', result)

    def test_local_variables_override_global_ones(self):
        code = 'my_var = 20\ndef f(self):\n    my_var = 10\n    my_'
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'local', result)

    def test_not_including_class_body_variables(self):
        code = 'class C(object):\n    my_var = 20\n' \
               '    def f(self):\n        a = 20\n        my_'
        result = self._assist(code)
        self.assert_completion_not_in_result('my_var', 'local', result)

    def test_nested_functions(self):
        code = 'def my_func():\n    func_var = 20\n    ' \
               'def inner_func():\n        a = 20\n        func'
        result = self._assist(code)
        self.assert_completion_in_result('func_var', 'local', result)

    def test_scope_endpoint_selection(self):
        code = "def my_func():\n    func_var = 20\n"
        result = self._assist(code)
        self.assert_completion_not_in_result('func_var', 'local', result)

    def test_scope_better_endpoint_selection(self):
        code = "if True:\n    def f():\n        my_var = 10\n    my_"
        result = self._assist(code)
        self.assert_completion_not_in_result('my_var', 'local', result)

    def test_imports_inside_function(self):
        code = "def f():\n    import sys\n    sy"
        result = self._assist(code)
        self.assert_completion_in_result('sys', 'imported', result)

    def test_imports_inside_function_dont_mix_with_globals(self):
        code = "def f():\n    import sys\nsy"
        result = self._assist(code)
        self.assert_completion_not_in_result('sys', 'local', result)

    def test_nested_classes_local_names(self):
        code = 'global_var = 10\n' \
               'def my_func():\n' \
               '    func_var = 20\n' \
               '    class C(object):\n' \
               '        def another_func(self):\n' \
               '            local_var = 10\n' \
               '            func'
        result = self._assist(code)
        self.assert_completion_in_result('func_var', 'local', result)

    def test_nested_classes_global(self):
        code = 'global_var = 10\n' \
               'def my_func():\n' \
               '    func_var = 20\n' \
               '    class C(object):\n' \
               '        def another_func(self):\n' \
               '            local_var = 10\n' \
               '            globa'
        result = self._assist(code)
        self.assert_completion_in_result('global_var', 'global', result)

    def test_nested_classes_global_function(self):
        code = 'global_var = 10\n' \
               'def my_func():\n' \
               '    func_var = 20\n' \
               '    class C(object):\n' \
               '        def another_func(self):\n' \
               '            local_var = 10\n' \
               '            my_f'
        result = self._assist(code)
        self.assert_completion_in_result('my_func', 'global', result)

    def test_proposing_function_parameters_in_functions(self):
        code = 'def my_func(my_param):\n    my_var = 20\n    my_'
        result = self._assist(code)
        self.assert_completion_in_result('my_param', 'local', result)

    def test_proposing_function_keyword_parameters_in_functions(self):
        code = 'def my_func(my_param, *my_list, **my_kws):\n' \
               '    my_var = 20\n' \
               '    my_'
        result = self._assist(code)
        self.assert_completion_in_result('my_param', 'local', result)
        self.assert_completion_in_result('my_list', 'local', result)
        self.assert_completion_in_result('my_kws', 'local', result)

    def test_not_proposing_unmatching_function_parameters_in_functions(self):
        code = "def my_func(my_param):\n    my_var = 20\n    you_"
        result = self._assist(code)
        self.assert_completion_not_in_result('my_param', 'local', result)

    def test_ignoring_current_statement(self):
        code = "my_var = 10\nmy_tuple = (10, \n           my_"
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_current_statement_brackets_continuation(self):
        code = "my_var = 10\n'hello'[10:\n        my_"
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_current_statement_explicit_continuation(self):
        code = "my_var = 10\nmy_var2 = 2 + \\\n          my_"
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignor_current_statement_while_the_first_stmnt_of_the_block(self):
        code = "my_var = 10\ndef f():\n    my_"
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignor_current_stmnt_while_current_line_ends_with_a_colon(self):
        code = "my_var = 10\nif my_:\n    pass"
        result = self._assist(code, 18)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_string_contents(self):
        code = "my_var = '('\nmy_"
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_comment_contents(self):
        code = "my_var = 10 #(\nmy_"
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_string_contents_backslash_plus_quotes(self):
        code = "my_var = '\\''\nmy_"
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_string_contents_backslash_plus_backslash(self):
        code = "my_var = '\\\\'\nmy_"
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_not_proposing_later_defined_variables_in_current_block(self):
        code = "my_\nmy_var = 10\n"
        result = self._assist(code, 3, later_locals=False)
        self.assert_completion_not_in_result('my_var', 'global', result)

    def test_not_proposing_later_defined_variables_in_current_function(self):
        code = "def f():\n    my_\n    my_var = 10\n"
        result = self._assist(code, 16, later_locals=False)
        self.assert_completion_not_in_result('my_var', 'local', result)

    def test_ignoring_string_contents_with_triple_quotes(self):
        code = "my_var = '''(\n'('''\nmy_"
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignoring_string_contents_with_triple_quotes_and_backslash(self):
        code = 'my_var = """\\"""("""\nmy_'
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_ignor_str_contents_with_triple_quotes_and_double_backslash(self):
        code = 'my_var = """\\\\"""\nmy_'
        result = self._assist(code)
        self.assert_completion_in_result('my_var', 'global', result)

    def test_reporting_params_when_in_the_first_line_of_a_function(self):
        code = 'def f(param):\n    para'
        result = self._assist(code)
        self.assert_completion_in_result('param', 'local', result)

    def test_code_assist_when_having_a_two_line_function_header(self):
        code = 'def f(param1,\n      param2):\n    para'
        result = self._assist(code)
        self.assert_completion_in_result('param1', 'local', result)

    def test_code_assist_with_function_with_two_line_return(self):
        code = 'def f(param1, param2):\n    return(param1,\n           para'
        result = self._assist(code)
        self.assert_completion_in_result('param2', 'local', result)

    def test_get_definition_location(self):
        code = 'def a_func():\n    pass\na_func()'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, 1), result)

    def test_get_definition_location_underlined_names(self):
        code = 'def a_sample_func():\n    pass\na_sample_func()'
        result = get_definition_location(self.project, code, len(code) - 11)
        self.assertEqual((None, 1), result)

    def test_get_definition_location_dotted_names_method(self):
        code = 'class AClass(object):\n' \
               '    @staticmethod\n' \
               '    def a_method():\n' \
               '        pass\n' \
               'AClass.a_method()'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, 3), result)

    def test_get_definition_location_dotted_names_property(self):
        code = 'class AClass(object):\n' \
               '    @property\n' \
               '    @somedecorator\n' \
               '    def a_method():\n' \
               '        pass\n' \
               'AClass.a_method()'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, 4), result)

    def test_get_definition_location_dotted_names_free_function(self):
        code = '@custom_decorator\n' \
               'def a_method():\n' \
               '    pass\n' \
               'a_method()'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, 2), result)

    @testutils.only_for_versions_higher('3.5')
    def test_get_definition_location_dotted_names_async_def(self):
        code = 'class AClass(object):\n' \
               '    @property\n' \
               '    @decorator2\n' \
               '    async def a_method():\n' \
               '        pass\n' \
               'AClass.a_method()'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, 4), result)

    def test_get_definition_location_dotted_names_class(self):
        code = '@custom_decorator\n' \
               'class AClass(object):\n' \
               '    def a_method():\n' \
               '        pass\n' \
               'AClass.a_method()'
        result = get_definition_location(self.project, code, len(code) - 12)
        self.assertEqual((None, 2), result)

    def test_get_definition_location_dotted_names_with_space(self):
        code = 'class AClass(object):\n' \
               '    @staticmethod\n' \
               '    def a_method():\n' \
               '        \n' \
               '        pass\n' \
               'AClass.a_method()'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, 3), result)

    def test_get_definition_location_dotted_names_inline_body(self):
        code = 'class AClass(object):\n' \
               '    @staticmethod\n' \
               '    def a_method(): pass\n' \
               'AClass.a_method()'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, 3), result)

    def test_get_definition_location_dotted_names_inline_body_split_arg(self):
        code = 'class AClass(object):\n' \
               '    @staticmethod\n' \
               '    def a_method(\n' \
               '        self,\n' \
               '        arg1\n' \
               '    ): pass\n' \
               'AClass.a_method()'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, 3), result)

    def test_get_definition_location_dotted_module_names(self):
        module_resource = testutils.create_module(self.project, 'mod')
        module_resource.write('def a_func():\n    pass\n')
        code = 'import mod\nmod.a_func()'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((module_resource, 1), result)

    def test_get_definition_location_for_nested_packages(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        pkg1 = testutils.create_package(self.project, 'pkg1')
        pkg2 = testutils.create_package(self.project, 'pkg2', pkg1)
        mod1.write('import pkg1.pkg2.mod2')

        init_dot_py = pkg2.get_child('__init__.py')
        found_pyname = get_definition_location(self.project, mod1.read(),
                                               mod1.read().index('pkg2') + 1)
        self.assertEqual(init_dot_py, found_pyname[0])

    def test_get_definition_location_unknown(self):
        code = 'a_func()\n'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, None), result)

    def test_get_definition_location_dot_spaces(self):
        code = 'class AClass(object):\n    ' \
               '@staticmethod\n    def a_method():\n' \
               '        pass\nAClass.\\\n     a_method()'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, 3), result)

    def test_get_definition_location_dot_line_break_inside_parens(self):
        code = 'class A(object):\n    def a_method(self):\n        pass\n' + \
               '(A.\na_method)'
        result = get_definition_location(self.project, code,
                                         code.rindex('a_method') + 1)
        self.assertEqual((None, 2), result)

    def test_if_scopes_in_other_scopes_for_get_definition_location(self):
        code = 'def f(a_var):\n    pass\na_var = 10\n' + \
               'if True:\n' + \
               '    print(a_var)\n'
        result = get_definition_location(self.project, code, len(code) - 3)
        self.assertEqual((None, 3), result)

    def test_get_definition_location_false_triple_quoted_string(self):
        code = dedent('''\
            def foo():
                a = 0
                p = "foo"""

            def bar():
                a = 1
                a += 1
        ''')
        result = get_definition_location(self.project, code, code.index("a += 1"))
        self.assertEqual((None, 6), result)

    def test_code_assists_in_parens(self):
        code = 'def a_func(a_var):\n    pass\na_var = 10\na_func(a_'
        result = self._assist(code)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_simple_type_inferencing(self):
        code = 'class Sample(object):\n' \
               '    def __init__(self, a_param):\n' \
               '        pass\n' \
               '    def a_method(self):\n' \
               '        pass\n' \
               'Sample("hey").a_'
        result = self._assist(code)
        self.assert_completion_in_result('a_method', 'attribute', result)

    def test_proposals_sorter(self):
        code = 'def my_sample_function(self):\n' + \
               '    my_sample_var = 20\n' + \
               '    my_sample_'
        proposals = sorted_proposals(self._assist(code))
        self.assertEqual('my_sample_var', proposals[0].name)
        self.assertEqual('my_sample_function', proposals[1].name)

    def test_proposals_sorter_for_methods_and_attributes(self):
        code = 'class A(object):\n' + \
               '    def __init__(self):\n' + \
               '        self.my_a_var = 10\n' + \
               '    def my_b_func(self):\n' + \
               '        pass\n' + \
               '    def my_c_func(self):\n' + \
               '        pass\n' + \
               'a_var = A()\n' + \
               'a_var.my_'
        proposals = sorted_proposals(self._assist(code))
        self.assertEqual('my_b_func', proposals[0].name)
        self.assertEqual('my_c_func', proposals[1].name)
        self.assertEqual('my_a_var', proposals[2].name)

    def test_proposals_sorter_for_global_methods_and_funcs(self):
        code = 'def my_b_func(self):\n' + \
               '    pass\n' + \
               'my_a_var = 10\n' + \
               'my_'
        proposals = sorted_proposals(self._assist(code))
        self.assertEqual('my_b_func', proposals[0].name)
        self.assertEqual('my_a_var', proposals[1].name)

    def test_proposals_sorter_underlined_methods(self):
        code = 'class A(object):\n' + \
               '    def _my_func(self):\n' + \
               '        self.my_a_var = 10\n' + \
               '    def my_func(self):\n' + \
               '        pass\n' + \
               'a_var = A()\n' + \
               'a_var.'
        proposals = sorted_proposals(self._assist(code))
        self.assertEqual('my_func', proposals[0].name)
        self.assertEqual('_my_func', proposals[1].name)

    def test_proposals_sorter_and_scope_prefs(self):
        code = 'my_global_var = 1\n' \
               'def func(self):\n' \
               '    my_local_var = 2\n' \
               '    my_'
        result = self._assist(code)
        proposals = sorted_proposals(result, scopepref=['global', 'local'])
        self.assertEqual('my_global_var', proposals[0].name)
        self.assertEqual('my_local_var', proposals[1].name)

    def test_proposals_sorter_and_type_prefs(self):
        code = 'my_global_var = 1\n' \
               'def my_global_func(self):\n' \
               '    pass\n' \
               'my_'
        result = self._assist(code)
        proposals = sorted_proposals(result, typepref=['instance', 'function'])
        self.assertEqual('my_global_var', proposals[0].name)
        self.assertEqual('my_global_func', proposals[1].name)

    def test_proposals_sorter_and_missing_type_in_typepref(self):
        code = 'my_global_var = 1\n' \
               'def my_global_func():\n' \
               '    pass\n' \
               'my_'
        result = self._assist(code)
        proposals = sorted_proposals(result, typepref=['function'])  # noqa

    def test_get_pydoc_unicode(self):
        src = u'# coding: utf-8\ndef foo():\n  u"юникод-объект"'
        doc = get_doc(self.project, src, src.index('foo') + 1)
        self.assertTrue(isinstance(doc, unicode))
        self.assertTrue(u'юникод-объект' in doc)

    def test_get_pydoc_utf8_bytestring(self):
        src = u'# coding: utf-8\ndef foo():\n  "байтстринг"'
        doc = get_doc(self.project, src, src.index('foo') + 1)
        self.assertTrue(isinstance(doc, unicode))
        self.assertTrue(u'байтстринг' in doc)

    def test_get_pydoc_for_functions(self):
        src = 'def a_func():\n' \
              '    """a function"""\n' \
              '    a_var = 10\n' \
              'a_func()'
        self.assertTrue(get_doc(self.project, src, len(src) - 4).
                        endswith('a function'))
        get_doc(self.project, src, len(src) - 4).index('a_func()')

    def test_get_pydoc_for_classes(self):
        src = 'class AClass(object):\n    pass\n'
        get_doc(self.project, src, src.index('AClass') + 1).index('AClass')

    def test_get_pydoc_for_classes_with_init(self):
        src = 'class AClass(object):\n    def __init__(self):\n        pass\n'
        get_doc(self.project, src, src.index('AClass') + 1).index('AClass')

    def test_get_pydoc_for_modules(self):
        mod = testutils.create_module(self.project, 'mod')
        mod.write('"""a module"""\n')
        src = 'import mod\nmod'
        self.assertEqual('a module', get_doc(self.project, src, len(src) - 1))

    def test_get_pydoc_for_builtins(self):
        src = 'print(object)\n'
        self.assertTrue(get_doc(self.project, src,
                                src.index('obj')) is not None)

    def test_get_pydoc_for_methods_should_include_class_name(self):
        src = 'class AClass(object):\n' \
              '    def a_method(self):\n'\
              '        """hey"""\n' \
              '        pass\n'
        doc = get_doc(self.project, src, src.index('a_method') + 1)
        doc.index('AClass.a_method')
        doc.index('hey')

    def test_get_pydoc_for_meths_should_inc_methods_from_super_classes(self):
        src = 'class A(object):\n' \
              '    def a_method(self):\n' \
              '        """hey1"""\n' \
              '        pass\n' \
              'class B(A):\n' \
              '    def a_method(self):\n' \
              '        """hey2"""\n' \
              '        pass\n'
        doc = get_doc(self.project, src, src.rindex('a_method') + 1)
        doc.index('A.a_method')
        doc.index('hey1')
        doc.index('B.a_method')
        doc.index('hey2')

    def test_get_pydoc_for_classes_should_name_super_classes(self):
        src = 'class A(object):\n    pass\n' \
              'class B(A):\n    pass\n'
        doc = get_doc(self.project, src, src.rindex('B') + 1)
        doc.index('B(A)')

    def test_get_pydoc_for_builtin_functions(self):
        src = 's = "hey"\ns.replace\n'
        doc = get_doc(self.project, src, src.rindex('replace') + 1)
        self.assertTrue(doc is not None)

    def test_commenting_errors_before_offset(self):
        src = 'lsjd lsjdf\ns = "hey"\ns.replace()\n'
        doc = get_doc(self.project, src, src.rindex('replace') + 1)  # noqa

    def test_proposing_variables_defined_till_the_end_of_scope(self):
        code = 'if True:\n    a_v\na_var = 10\n'
        result = self._assist(code, code.index('a_v') + 3)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_completing_in_uncomplete_try_blocks(self):
        code = 'try:\n    a_var = 10\n    a_'
        result = self._assist(code)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_completing_in_uncomplete_try_blocks_in_functions(self):
        code = 'def a_func():\n    try:\n        a_var = 10\n        a_'
        result = self._assist(code)
        self.assert_completion_in_result('a_var', 'local', result)

    def test_already_complete_try_blocks_with_finally(self):
        code = 'def a_func():\n    try:\n        a_var = 10\n        a_'
        result = self._assist(code)
        self.assert_completion_in_result('a_var', 'local', result)

    def test_already_complete_try_blocks_with_finally2(self):
        code = 'try:\n    a_var = 10\n    a_\nfinally:\n    pass\n'
        result = self._assist(code, code.rindex('a_') + 2)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_already_complete_try_blocks_with_except(self):
        code = 'try:\n    a_var = 10\n    a_\nexcept Exception:\n    pass\n'
        result = self._assist(code, code.rindex('a_') + 2)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_already_complete_try_blocks_with_except2(self):
        code = 'a_var = 10\ntry:\n    ' \
               'another_var = a_\n    another_var = 10\n' \
               'except Exception:\n    pass\n'
        result = self._assist(code, code.rindex('a_') + 2)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_completing_ifs_in_uncomplete_try_blocks(self):
        code = 'try:\n    if True:\n        a_var = 10\n    a_'
        result = self._assist(code)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_completing_ifs_in_uncomplete_try_blocks2(self):
        code = 'try:\n    if True:\n        a_var = 10\n        a_'
        result = self._assist(code)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_completing_excepts_in_uncomplete_try_blocks(self):
        code = 'try:\n    pass\nexcept Exc'
        result = self._assist(code)
        self.assert_completion_in_result('Exception', 'builtin', result)

    def test_and_normal_complete_blocks_and_single_fixing(self):
        code = 'try:\n    range.\nexcept:\n    pass\n'
        result = self._assist(code, code.index('.'), maxfixes=1)  # noqa

    def test_nested_blocks(self):
        code = 'a_var = 10\ntry:\n    try:\n        a_v'
        result = self._assist(code)
        self.assert_completion_in_result('a_var', 'global', result)

    def test_proposing_function_keywords_when_calling(self):
        code = 'def f(p):\n    pass\nf(p'
        result = self._assist(code)
        self.assert_completion_in_result('p=', 'parameter_keyword', result)

    def test_proposing_function_keywords_when_calling_for_non_functions(self):
        code = 'f = 1\nf(p'
        result = self._assist(code)  # noqa

    def test_proposing_function_keywords_when_calling_extra_spaces(self):
        code = 'def f(p):\n    pass\nf( p'
        result = self._assist(code)
        self.assert_completion_in_result('p=', 'parameter_keyword', result)

    def test_proposing_function_keywords_when_calling_on_second_argument(self):
        code = 'def f(p1, p2):\n    pass\nf(1, p'
        result = self._assist(code)
        self.assert_completion_in_result('p2=', 'parameter_keyword', result)

    def test_proposing_function_keywords_when_calling_not_proposing_args(self):
        code = 'def f(p1, *args):\n    pass\nf(1, a'
        result = self._assist(code)
        self.assert_completion_not_in_result('args=', 'parameter_keyword',
                                             result)

    def test_propos_function_kwrds_when_call_with_no_noth_after_parens(self):
        code = 'def f(p):\n    pass\nf('
        result = self._assist(code)
        self.assert_completion_in_result('p=', 'parameter_keyword', result)

    def test_propos_function_kwrds_when_call_with_no_noth_after_parens2(self):
        code = 'def f(p):\n    pass\ndef g():\n    h = f\n    f('
        result = self._assist(code)
        self.assert_completion_in_result('p=', 'parameter_keyword', result)

    def test_codeassists_before_opening_of_parens(self):
        code = 'def f(p):\n    pass\na_var = 1\nf(1)\n'
        result = self._assist(code, code.rindex('f') + 1)
        self.assert_completion_not_in_result('a_var', 'global', result)

    def test_codeassist_before_single_line_indents(self):
        code = 'myvar = 1\nif True:\n    (myv\nif True:\n    pass\n'
        result = self._assist(code, code.rindex('myv') + 3)
        self.assert_completion_not_in_result('myvar', 'local', result)

    def test_codeassist_before_line_indents_in_a_blank_line(self):
        code = 'myvar = 1\nif True:\n    \nif True:\n    pass\n'
        result = self._assist(code, code.rindex('    ') + 4)
        self.assert_completion_not_in_result('myvar', 'local', result)

    def test_simple_get_calltips(self):
        src = 'def f():\n    pass\nvar = f()\n'
        doc = get_calltip(self.project, src, src.rindex('f'))
        self.assertEqual('f()', doc)

    def test_get_calltips_for_classes(self):
        src = 'class C(object):\n' \
              '    def __init__(self):\n        pass\nC('
        doc = get_calltip(self.project, src, len(src) - 1)
        self.assertEqual('C.__init__(self)', doc)

    def test_get_calltips_for_objects_with_call(self):
        src = 'class C(object):\n' \
              '    def __call__(self, p):\n        pass\n' \
              'c = C()\nc(1,'
        doc = get_calltip(self.project, src, src.rindex('c'))
        self.assertEqual('C.__call__(self, p)', doc)

    def test_get_calltips_and_including_module_name(self):
        src = 'class C(object):\n' \
              '    def __call__(self, p):\n        pass\n' \
              'c = C()\nc(1,'
        mod = testutils.create_module(self.project, 'mod')
        mod.write(src)
        doc = get_calltip(self.project, src, src.rindex('c'), mod)
        self.assertEqual('mod.C.__call__(self, p)', doc)

    def test_get_calltips_and_including_module_name_2(self):
        src = 'range()\n'
        doc = get_calltip(self.project, src, 1, ignore_unknown=True)
        self.assertTrue(doc is None)

    def test_removing_self_parameter(self):
        src = 'class C(object):\n' \
              '    def f(self):\n'\
              '        pass\n' \
              'C().f()'
        doc = get_calltip(self.project, src, src.rindex('f'), remove_self=True)
        self.assertEqual('C.f()', doc)

    def test_removing_self_parameter_and_more_than_one_parameter(self):
        src = 'class C(object):\n' \
              '    def f(self, p1):\n'\
              '        pass\n' \
              'C().f()'
        doc = get_calltip(self.project, src, src.rindex('f'), remove_self=True)
        self.assertEqual('C.f(p1)', doc)

    def test_lambda_calltip(self):
        src = 'foo = lambda x, y=1: None\n' \
              'foo()'
        doc = get_calltip(self.project, src, src.rindex('f'))
        self.assertEqual(doc, 'lambda(x, y)')

    def test_keyword_before_parens(self):
        code = 'if (1).:\n pass'
        result = self._assist(code, offset=len('if (1).'))
        self.assertTrue(result)

    # TESTING PROPOSAL'S KINDS AND TYPES.
    # SEE RELATION MATRIX IN `CompletionProposal`'s DOCSTRING

    def test_local_variable_completion_proposal(self):
        code = 'def foo():\n  xvar = 5\n  x'
        result = self._assist(code)
        self.assert_completion_in_result('xvar', 'local', result, 'instance')

    def test_global_variable_completion_proposal(self):
        code = 'yvar = 5\ny'
        result = self._assist(code)
        self.assert_completion_in_result('yvar', 'global', result, 'instance')

    def test_builtin_variable_completion_proposal(self):
        for varname in ('False', 'True'):
            result = self._assist(varname[0])
            self.assert_completion_in_result(varname, 'builtin', result,
                                             type='instance')

    def test_attribute_variable_completion_proposal(self):
        code = 'class AClass(object):\n  def foo(self):\n    ' \
               'self.bar = 1\n    self.b'
        result = self._assist(code)
        self.assert_completion_in_result('bar', 'attribute', result,
                                         type='instance')

    def test_local_class_completion_proposal(self):
        code = 'def foo():\n  class LocalClass(object): pass\n  Lo'
        result = self._assist(code)
        self.assert_completion_in_result('LocalClass', 'local', result,
                                         type='class')

    def test_global_class_completion_proposal(self):
        code = 'class GlobalClass(object): pass\nGl'
        result = self._assist(code)
        self.assert_completion_in_result('GlobalClass', 'global', result,
                                         type='class')

    def test_builtin_class_completion_proposal(self):
        for varname in ('object', 'dict', 'file'):
            result = self._assist(varname[0])
            self.assert_completion_in_result(varname, 'builtin', result,
                                             type='class')

    def test_attribute_class_completion_proposal(self):
        code = 'class Outer(object):\n  class Inner(object): pass\nOuter.'
        result = self._assist(code)
        self.assert_completion_in_result('Inner', 'attribute', result,
                                         type='class')

    def test_local_function_completion_proposal(self):
        code = 'def outer():\n  def inner(): pass\n  in'
        result = self._assist(code)
        self.assert_completion_in_result('inner', 'local', result,
                                         type='function')

    def test_global_function_completion_proposal(self):
        code = 'def foo(): pass\nf'
        result = self._assist(code)
        self.assert_completion_in_result('foo', 'global', result,
                                         type='function')

    def test_builtin_function_completion_proposal(self):
        code = 'a'
        result = self._assist(code)
        for expected in ('all', 'any', 'abs'):
            self.assert_completion_in_result(expected, 'builtin', result,
                                             type='function')

    def test_attribute_function_completion_proposal(self):
        code = 'class Some(object):\n  def method(self):\n    self.'
        result = self._assist(code)
        self.assert_completion_in_result('method', 'attribute', result,
                                         type='function')

    def test_local_module_completion_proposal(self):
        code = 'def foo():\n  import types\n  t'
        result = self._assist(code)
        self.assert_completion_in_result('types', 'imported', result,
                                         type='module')

    def test_global_module_completion_proposal(self):
        code = 'import operator\no'
        result = self._assist(code)
        self.assert_completion_in_result('operator', 'imported', result,
                                         type='module')

    def test_attribute_module_completion_proposal(self):
        code = 'class Some(object):\n  import os\nSome.o'
        result = self._assist(code)
        self.assert_completion_in_result('os', 'imported', result,
                                         type='module')

    def test_builtin_exception_completion_proposal(self):
        code = 'def blah():\n  Z'
        result = self._assist(code)
        self.assert_completion_in_result('ZeroDivisionError', 'builtin',
                                         result, type='class')

    def test_keyword_completion_proposal(self):
        code = 'f'
        result = self._assist(code)
        self.assert_completion_in_result('for', 'keyword', result, type=None)
        self.assert_completion_in_result('from', 'keyword', result, type=None)

    def test_parameter_keyword_completion_proposal(self):
        code = 'def func(abc, aloha, alpha, amigo): pass\nfunc(a'
        result = self._assist(code)
        for expected in ('abc=', 'aloha=', 'alpha=', 'amigo='):
            self.assert_completion_in_result(expected, 'parameter_keyword',
                                             result, type=None)

    def test_object_path_global(self):
        code = 'GLOBAL_VARIABLE = 42\n'
        resource = testutils.create_module(self.project, 'mod')
        resource.write(code)
        result = get_canonical_path(self.project, resource, 1)
        mod_path = os.path.join(self.project.address, 'mod.py')
        self.assertEqual(
            result, [(mod_path, 'MODULE'),
                     ('GLOBAL_VARIABLE', 'VARIABLE')])

    def test_object_path_attribute(self):
        code = 'class Foo(object):\n' \
               '    attr = 42\n'
        resource = testutils.create_module(self.project, 'mod')
        resource.write(code)
        result = get_canonical_path(self.project, resource, 24)
        mod_path = os.path.join(self.project.address, 'mod.py')
        self.assertEqual(
            result, [(mod_path, 'MODULE'), ('Foo', 'CLASS'),
                     ('attr', 'VARIABLE')])

    def test_object_path_subclass(self):
        code = 'class Foo(object):\n' \
               '    class Bar(object):\n' \
               '        pass\n'
        resource = testutils.create_module(self.project, 'mod')
        resource.write(code)
        result = get_canonical_path(self.project, resource, 30)
        mod_path = os.path.join(self.project.address, 'mod.py')
        self.assertEqual(
            result, [(mod_path, 'MODULE'), ('Foo', 'CLASS'),
                     ('Bar', 'CLASS')])

    def test_object_path_method_parameter(self):
        code = 'class Foo(object):\n' \
               '    def bar(self, a, b, c):\n' \
               '        pass\n'
        resource = testutils.create_module(self.project, 'mod')
        resource.write(code)
        result = get_canonical_path(self.project, resource, 41)
        mod_path = os.path.join(self.project.address, 'mod.py')
        self.assertEqual(
            result, [(mod_path, 'MODULE'), ('Foo', 'CLASS'),
                     ('bar', 'FUNCTION'), ('b', 'PARAMETER')])

    def test_object_path_variable(self):
        code = 'def bar(a):\n' \
               '    x = a + 42\n'
        resource = testutils.create_module(self.project, 'mod')
        resource.write(code)
        result = get_canonical_path(self.project, resource, 17)
        mod_path = os.path.join(self.project.address, 'mod.py')
        self.assertEqual(
            result, [(mod_path, 'MODULE'), ('bar', 'FUNCTION'),
                     ('x', 'VARIABLE')])


class CodeAssistInProjectsTest(unittest.TestCase):
    def setUp(self):
        super(CodeAssistInProjectsTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        samplemod = testutils.create_module(self.project, 'samplemod')
        code = 'class SampleClass(object):\n' \
               '    def sample_method():\n        pass\n\n' \
               'def sample_func():\n    pass\n' \
               'sample_var = 10\n\n' \
               'def _underlined_func():\n    pass\n\n'
        samplemod.write(code)
        package = testutils.create_package(self.project, 'package')
        nestedmod = testutils.create_module(self.project,  # noqa
                                            'nestedmod', package)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(self.__class__, self).tearDown()

    def _assist(self, code, resource=None, **kwds):
        return code_assist(self.project, code, len(code), resource, **kwds)

    def assert_completion_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                return
        self.fail('completion <%s> not proposed' % name)

    def assert_completion_not_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                self.fail('completion <%s> was proposed' % name)

    def test_simple_import(self):
        code = 'import samplemod\nsample'
        result = self._assist(code)
        self.assert_completion_in_result('samplemod', 'imported', result)

    def test_from_import_class(self):
        code = 'from samplemod import SampleClass\nSample'
        result = self._assist(code)
        self.assert_completion_in_result('SampleClass', 'imported', result)

    def test_from_import_function(self):
        code = 'from samplemod import sample_func\nsample'
        result = self._assist(code)
        self.assert_completion_in_result('sample_func', 'imported', result)

    def test_from_import_variable(self):
        code = 'from samplemod import sample_var\nsample'
        result = self._assist(code)
        self.assert_completion_in_result('sample_var', 'imported', result)

    def test_from_imports_inside_functions(self):
        code = 'def f():\n    from samplemod import SampleClass\n    Sample'
        result = self._assist(code)
        self.assert_completion_in_result('SampleClass', 'imported', result)

    def test_from_import_only_imports_imported(self):
        code = 'from samplemod import sample_func\nSample'
        result = self._assist(code)
        self.assert_completion_not_in_result('SampleClass', 'global', result)

    def test_from_import_star(self):
        code = 'from samplemod import *\nSample'
        result = self._assist(code)
        self.assert_completion_in_result('SampleClass', 'imported', result)

    def test_from_import_star2(self):
        code = 'from samplemod import *\nsample'
        result = self._assist(code)
        self.assert_completion_in_result('sample_func', 'imported', result)
        self.assert_completion_in_result('sample_var', 'imported', result)

    def test_from_import_star_not_imporing_underlined(self):
        code = 'from samplemod import *\n_under'
        result = self._assist(code)
        self.assert_completion_not_in_result('_underlined_func', 'global',
                                             result)

    def test_from_package_import_mod(self):
        code = 'from package import nestedmod\nnest'
        result = self._assist(code)
        self.assert_completion_in_result('nestedmod', 'imported', result)

    def test_completing_after_dot(self):
        code = 'class SampleClass(object):\n' \
               '    def sample_method(self):\n' \
               '        pass\n' \
               'SampleClass.sam'
        result = self._assist(code)
        self.assert_completion_in_result('sample_method', 'attribute', result)

    def test_completing_after_multiple_dots(self):
        code = 'class Class1(object):\n' \
               '    class Class2(object):\n' \
               '        def sample_method(self):\n' \
               '            pass\n' \
               'Class1.Class2.sam'
        result = self._assist(code)
        self.assert_completion_in_result('sample_method', 'attribute', result)

    def test_completing_after_self_dot(self):
        code = 'class Sample(object):\n' \
               '    def method1(self):\n' \
               '        pass\n' \
               '    def method2(self):\n' \
               '        self.m'
        result = self._assist(code)
        self.assert_completion_in_result('method1', 'attribute', result)

    def test_result_start_offset_for_dotted_completions(self):
        code = 'class Sample(object):\n' \
               '    def method1(self):\n' \
               '        pass\n' \
               'Sample.me'
        self.assertEqual(len(code) - 2, starting_offset(code, len(code)))

    def test_backslash_after_dots(self):
        code = 'class Sample(object):\n' \
               '    def a_method(self):\n' \
               '        pass\n' \
               'Sample.\\\n       a_m'
        result = self._assist(code)
        self.assert_completion_in_result('a_method', 'attribute', result)

    def test_not_proposing_global_names_after_dot(self):
        code = 'class Sample(object):\n' \
               '    def a_method(self):\n' \
               '        pass\n' \
               'Sample.'
        result = self._assist(code)
        self.assert_completion_not_in_result('Sample', 'global', result)

    def test_assist_on_relative_imports(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod1.write('def a_func():\n    pass\n')
        code = 'import mod1\nmod1.'
        result = self._assist(code, resource=mod2)
        self.assert_completion_in_result('a_func', 'imported', result)

    def test_get_location_on_relative_imports(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod1.write('def a_func():\n    pass\n')
        code = 'import mod1\nmod1.a_func\n'
        result = get_definition_location(self.project, code,
                                         len(code) - 2, mod2)
        self.assertEqual((mod1, 1), result)

    def test_get_definition_location_for_builtins(self):
        code = 'import sys\n'
        result = get_definition_location(self.project, code,
                                         len(code) - 2)
        self.assertEqual((None, None), result)

    def test_get_doc_on_relative_imports(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod1.write('def a_func():\n    """hey"""\n    pass\n')
        code = 'import mod1\nmod1.a_func\n'
        result = get_doc(self.project, code, len(code) - 2, mod2)
        self.assertTrue(result.endswith('hey'))

    def test_get_doc_on_from_import_module(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('"""mod1 docs"""\nvar = 1\n')
        code = 'from mod1 import var\n'
        result = get_doc(self.project, code, code.index('mod1'))
        result.index('mod1 docs')

    def test_fixing_errors_with_maxfixes_in_resources(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'def f():\n    sldj sldj\ndef g():\n    ran'
        mod.write(code)
        result = self._assist(code, maxfixes=2, resource=mod)
        self.assertTrue(len(result) > 0)

    def test_completing_names_after_from_import(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('myvar = None\n')
        result = self._assist('from mod1 import myva', resource=mod2)
        self.assertTrue(len(result) > 0)
        self.assert_completion_in_result('myvar', 'global', result)

    def test_completing_names_after_from_import_and_sorted_proposals(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('myvar = None\n')
        result = self._assist('from mod1 import myva', resource=mod2)
        result = sorted_proposals(result)
        self.assertTrue(len(result) > 0)
        self.assert_completion_in_result('myvar', 'global', result)

    def test_completing_names_after_from_import2(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('myvar = None\n')
        result = self._assist('from mod1 import ', resource=mod2)
        self.assertTrue(len(result) > 0)
        self.assert_completion_in_result('myvar', 'global', result)

    def test_starting_expression(self):
        code = 'l = list()\nl.app'
        self.assertEqual('l.app', starting_expression(code, len(code)))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(CodeAssistTest))
    result.addTests(unittest.makeSuite(CodeAssistInProjectsTest))
    return result

if __name__ == '__main__':
    unittest.main()
